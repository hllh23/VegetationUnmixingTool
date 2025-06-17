# 核心解混算法模块
import numpy as np
from scipy.optimize import lsq_linear
from osgeo import gdal
import multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory
import sys
import gc





def compute_user_selected_ndvi_swir32(
    input_path: str,
    nir_band: int,
    red_band: int,
    swir3_band: int,
    swir2_band: int
) -> tuple:
    """
    计算指定波段的NDVI和SWIR32比值
    
    参数：
    input_path (str): 输入栅格文件路径
    nir_band (int): 近红外波段编号 (1-based)
    red_band (int): 红波段编号 (1-based)
    swir3_band (int): SWIR3波段编号 (1-based)
    swir2_band (int): SWIR2波段编号 (1-based)
    
    返回：
    tuple: (ndvi数组, swir32数组, 地理变换矩阵, 投影信息)
    
    异常：
    ValueError: 当文件无法打开或波段编号无效时抛出
    """
    ds = gdal.Open(input_path, gdal.GA_ReadOnly)
    if not ds:
        raise ValueError(f"无法打开栅格文件: {input_path}")

    try:
        # 验证波段编号有效性
        band_count = ds.RasterCount
        for band, name in zip(
            [nir_band, red_band, swir3_band, swir2_band],
            ["NIR", "Red", "SWIR3", "SWIR2"]
        ):
            if not 1 <= band <= band_count:
                raise ValueError(
                    f"无效的{name}波段编号 {band}，"
                    f"文件包含{band_count}个波段"
                )

        # 读取波段数据
        def read_band(band_num: int) -> np.ndarray:
            """读取并验证波段数据"""
            band = ds.GetRasterBand(band_num)
            array = band.ReadAsArray().astype(np.float32)
            if array is None:
                raise ValueError(f"无法读取波段 {band_num} 的数据")
            return array

        nir = read_band(nir_band)
        red = read_band(red_band)
        swir3 = read_band(swir3_band)
        swir2 = read_band(swir2_band)

        # 计算NDVI（分母为零时设为NaN）
        denominator_ndvi = nir + red
        ndvi = np.divide(
            nir - red,
            denominator_ndvi,
            out=np.zeros_like(denominator_ndvi, dtype=np.float32),
            where=denominator_ndvi != 0
        )

        # 计算SWIR32比值（分母为零时设为NaN）
        swir32 = np.divide(
            swir3,
            swir2,
            out=np.zeros_like(swir2, dtype=np.float32),
            where=swir2 != 0
        )

        return (
            ndvi,
            swir32,
            ds.GetGeoTransform(),
            ds.GetProjection()
        )

    finally:
        # 确保释放数据集资源
        if ds:
            ds = None


def unmix_pixel(m, E, precalc):
    """像素解混核心函数"""
    A, E3, C = precalc['A'], precalc['E3'], precalc['C']
    res = lsq_linear(A, m - E3, bounds=(0, np.inf))
    x, y = res.x
    if (f3 := 1 - x - y) >= 0:
        return np.round([x, y, f3], 3)
    
    d = precalc['E2'] - m
    denominator = precalc['C_squared']
    x_clamped = max(0.0, min(1.0, -(C @ d) / denominator)) if denominator >= 1e-10 else 0.5
    return np.round([x_clamped, 1-x_clamped, 0.0], 3)

# 行处理函数
def process_row_enhanced(args):    
    """增强的行处理函数"""
    (i, 
     band1_shm_name, band2_shm_name,
     land_use_shm_name, land_use_shape, land_use_dtype,
     selected_values,
     E_forest, E_nonforest,
     precalc_forest, precalc_nonforest) = args

    # 访问共享内存
    shm_band1 = SharedMemory(name=band1_shm_name)
    shm_band2 = SharedMemory(name=band2_shm_name)
    shm_land_use = SharedMemory(name=land_use_shm_name)
    
    try:
        band1 = np.ndarray(land_use_shape, dtype=np.float32, buffer=shm_band1.buf)
        band2 = np.ndarray(land_use_shape, dtype=np.float32, buffer=shm_band2.buf)
        land_use = np.ndarray(land_use_shape, dtype=land_use_dtype, buffer=shm_land_use.buf)

        row_result = np.zeros((3, land_use_shape[1]), dtype=np.float32)
        
        for j in range(land_use_shape[1]):
            # 获取当前像素特征值
            m = np.array([band1[i, j], band2[i, j]])
            
            # 判断地类类型
            is_forest = land_use[i, j] in selected_values
            
            # 选择解混参数
            if is_forest:
                res = unmix_pixel(m, E_forest, precalc_forest)
            else:
                res = unmix_pixel(m, E_nonforest, precalc_nonforest)
            
            row_result[:, j] = res
        
        return i, row_result
    finally:
        shm_band1.close()
        shm_band2.close()
        shm_land_use.close()
        if sys.platform == "win32":
            shm_band1.unlink()
            shm_band2.unlink()
            shm_land_use.unlink()

# 土地利用数据读取函数
def read_land_use(land_use_path: str) -> np.ndarray:
    """
    读取土地利用数据
    
    参数：
    land_use_path (str): 土地利用tif文件路径
    
    返回：
    np.ndarray: 土地利用数据数组
    
    异常：
    ValueError: 当文件无法打开时抛出
    """
    ds = gdal.Open(land_use_path, gdal.GA_ReadOnly)
    if not ds:
        raise ValueError(f"无法打开土地利用文件: {land_use_path}")
    
    try:
        band = ds.GetRasterBand(1)
        land_use = band.ReadAsArray().astype(np.int32)
        if land_use is None:
            raise ValueError("无法读取土地利用数据")
        return land_use
    finally:
        ds = None

# 解混主函数
def batch_unmix(ndvi, swir32, geo_transform, projection, output_path, 
                land_use_array, selected_values, E_forest, E_nonforest):
    """解混主函数（支持不同地类使用不同端元）"""
    # 数据一致性验证
    assert land_use_array.shape == ndvi.shape, "土地利用数据与NDVI数据尺寸不匹配"
    
    # 创建共享内存
    shm_band1 = SharedMemory(create=True, size=ndvi.nbytes)
    shm_band2 = SharedMemory(create=True, size=swir32.nbytes)
    shm_land_use = SharedMemory(create=True, size=land_use_array.nbytes)
    
    # 复制数据到共享内存
    np.ndarray(ndvi.shape, dtype=ndvi.dtype, buffer=shm_band1.buf)[:] = ndvi
    np.ndarray(swir32.shape, dtype=swir32.dtype, buffer=shm_band2.buf)[:] = swir32
    np.ndarray(land_use_array.shape, dtype=land_use_array.dtype, buffer=shm_land_use.buf)[:] = land_use_array

    # 预计算两种地类的解混参数
    def get_precalc(E):
        return {
            'A': E[:,:2] - E[:,2].reshape(-1,1),
            'E3': E[:,2],
            'E2': E[:,1],
            'C': E[:,0] - E[:,1],
            'C_squared': (E[:,0] - E[:,1]) @ (E[:,0] - E[:,1])
        }
    
    precalc_forest = get_precalc(E_forest)
    precalc_nonforest = get_precalc(E_nonforest)

    # 创建输出文件
    driver = gdal.GetDriverByName('GTiff')
    ds_out = driver.Create(
        output_path,
        ndvi.shape[1],
        ndvi.shape[0],
        3,
        gdal.GDT_Float32
    )
    ds_out.SetGeoTransform(geo_transform)
    ds_out.SetProjection(projection)

    # 准备并行参数
    shape = ndvi.shape
    dtype = ndvi.dtype
    args = [
        (i, 
         shm_band1.name, shm_band2.name,
         shm_land_use.name, land_use_array.shape, land_use_array.dtype,
         selected_values,
         E_forest, E_nonforest,
         precalc_forest, precalc_nonforest)
        for i in range(shape[0])
    ]

    # 并行处理
    with mp.Pool(mp.cpu_count()//2)as pool:
        print(mp.cpu_count())
        results = pool.imap(process_row_enhanced, args, chunksize=10)
        
        output = np.empty((3, shape[0], shape[1]), dtype=np.float32)
        for i, row_data in results:
            output[:, i, :] = row_data
            if i % 100 == 0:
                print(f'Processed {i+1}/{shape[0]} rows')

    # 写入结果
    for b in range(3):
        ds_out.GetRasterBand(b+1).WriteArray(output[b])
    
    # 清理资源
    shm_band1.close()
    shm_band1.unlink()
    shm_band2.close()
    shm_band2.unlink()
    shm_land_use.close()
    shm_land_use.unlink()
    ds_out = None
    gc.collect()

# 土地利用处理逻辑
def select_land_use_values(land_use_path: str, forst_value: str) -> tuple:
    """
    交互式选择林地对应值
    
    参数：
    land_use_path (str): 土地利用tif文件路径
    
    返回：
    tuple: (土地利用数组, 选中的值列表)
    """
    land_use = read_land_use(land_use_path)
    
    # 获取唯一值并排序
    unique_values = np.unique(land_use).tolist()
    print(f"检测到土地利用类型值：{unique_values}")
    

    selected_values = [int(v) for v in forst_value.split(",")]
    
    return land_use, selected_values


# 解混入口函数
def execute_unmixing_with_landuse(
    input_path: str,
    land_use_path: str,
    output_path: str,
    nir_band: int,
    red_band: int,
    swir3_band: int,
    swir2_band: int,
    forst_value: str,
    E_forest: np.ndarray = np.array([[0.85, 0.32, 0.11], [0.74, 1.05, 0.51]]),
    E_nonforest: np.ndarray = np.array([[0.72, 0.25, 0.11], [0.74, 1.05, 0.51]])
):
    """
    带土地利用判断的解混流程
    
    参数：
    input_path (str): 输入影像路径
    land_use_path (str): 土地利用数据路径
    output_path (str): 输出文件路径
    nir_band (int): 近红外波段号
    red_band (int): 红波段号
    swir3_band (int): SWIR3波段号
    swir2_band (int): SWIR2波段号
    E_forest (np.ndarray): 林地端元矩阵
    E_nonforest (np.ndarray): 非林地端元矩阵
    """
    try:
        # 步骤1：计算光谱指数
        ndvi, swir32, geo_transform, projection = compute_user_selected_ndvi_swir32(
            input_path, nir_band, red_band, swir3_band, swir2_band
        )
        
        # 步骤2：处理土地利用数据
        land_use_array, selected_values = select_land_use_values(land_use_path, forst_value) #GUI前

        
        # 步骤3：执行解混
        batch_unmix(
            ndvi=ndvi,
            swir32=swir32,
            geo_transform=geo_transform,
            projection=projection,
            output_path=output_path,
            land_use_array=land_use_array,
            selected_values=selected_values,
            E_forest=E_forest,
            E_nonforest=E_nonforest
        )
        
        print(f"解混完成，结果已保存至：{output_path}")
        
    except Exception as e:
        print(f"处理过程中发生错误：{str(e)}")
        raise

