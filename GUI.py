# 图形界面模块
from osgeo import gdal, osr, ogr
import numpy as np
from Core_Function import execute_unmixing_with_landuse

# GUI模块
from PyQt5.QtWidgets import (QMainWindow, QWidget, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QMessageBox, QComboBox, QGroupBox, QVBoxLayout, 
                             QDesktopWidget, QPlainTextEdit, QApplication)
from PyQt5.QtGui import (QIntValidator, QIcon)
from PyQt5.QtCore import Qt
import os

# 获取图标绝对路径
def get_icon_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "app_icon.ico")
    
    # 验证图标文件存在性
    if not os.path.exists(icon_path):
        raise FileNotFoundError(f"图标文件缺失: {icon_path}")
        
    return icon_path

def get_unique_values(file_path):
    """获取栅格文件的唯一值"""
    ds = gdal.Open(file_path)
    if ds is None:
        raise ValueError("无法打开文件")
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray()
    unique_values = np.unique(data)
    ds = None
    return unique_values

class UnmixingGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.heartbeat_listener = None
        self.initUI()
        self.start_heartbeat_server()
        
    def start_heartbeat_server(self):
        from multiprocessing.connection import Listener
        def listener_thread():
            address = ('localhost', 6000)
            listener = Listener(address, authkey=b'rs_unmixing')
            while True:
                conn = listener.accept()
                conn.close()
                        
    def initUI(self):
        # 主窗口设置（修改后的窗口初始化）
        self.setWindowIcon(QIcon(get_icon_path()))
        self.setWindowTitle('RS_Unmixing_Tool')
        
        # 自适应屏幕尺寸
        screen = QDesktopWidget().screenGeometry()
        self.resize(int(screen.width()*0.3), int(screen.height()*0.5))
        self.setMinimumSize(1000, 800)  # 添加最小尺寸限制
        self.center()  # 新增居中方法
        
        # 主部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(25)  # 控制组与组之间的间距
        
        # 创建界面组件（新增信息反馈栏）
        self.create_file_group(main_layout)
        self.create_param_group(main_layout)
        self.create_band_info_label(main_layout)
        self.create_run_button(main_layout)
        self.create_info_panel(main_layout)  # 新增方法
        
        # 修改后的样式表（适配不同分辨率）
        self.setStyleSheet("""
            QWidget { font-family: Microsoft YaHei; }  /* 添加字体族 */
            QGroupBox { 
                font-size: 18px;  /* 原16px */
                border: 2px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 1.5ex;
            }
            QLabel { 
                font-size: 18px;  /* 原16px */
                min-width: 140px; 
            }
            QComboBox, QLineEdit { 
                font-size: 18px;  /* 原16px */
                padding: 5px;
            }
            QGroupBox:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8F9F9, stop:1 #ECF0F1);
                border-radius: 5px;
            }                           
        """)

    # 新增方法：窗口居中
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # 新增方法：创建信息反馈面板
    def create_info_panel(self, layout):
        # 信息反馈组样式
        info_group = QGroupBox("信息反馈")
        info_group.setStyleSheet("""
            QGroupBox {
                font: bold 20px '微软雅黑';
                color: #2C3E50;
                margin-top: 15px;
                padding-top: 25px;
            }
        """)        
        self.info_text = QPlainTextEdit()
        self.info_text.setMaximumHeight(250)  # 新增高度限制
        self.info_text.setStyleSheet("font-size: 15px;")  # 单独字体设置
        vbox = QVBoxLayout()
        vbox.addWidget(self.info_text)
        info_group.setLayout(vbox)
        layout.addWidget(info_group, stretch=1)  # 调整布局比例
        
    # 在UnmixingGUI类中添加以下方法
    def create_file_group(self, layout):
        """创建文件选择组（修改后的完整实现）"""
        file_group = QGroupBox("文件输入")

        file_group.setStyleSheet("""
            QGroupBox {
                font: bold 20px '微软雅黑';
                color: #2C3E50;
                margin-top: 15px;
                padding-top: 25px;
            }
        """)       
        grid = QGridLayout()    
        
        # 遥感影像选择
        img_label = QLabel("遥感多光谱数据:")
        self.img_path = QLineEdit()
        img_btn = QPushButton("浏览...")
        img_btn.clicked.connect(lambda: self.select_input_file(self.img_path))
        
        # 新增土地利用文件选择
        landuse_label = QLabel("土地利用数据:")
        self.land_use_path = QLineEdit()
        landuse_btn = QPushButton("浏览...")
        landuse_btn.clicked.connect(lambda: self.select_land_use_file(self.land_use_path))  # 添加参数
        
        # 输出路径
        output_label = QLabel("输出路径:")
        self.output_path = QLineEdit()
        output_btn = QPushButton("浏览...")
        # 在创建输出路径按钮的位置：
        output_btn.clicked.connect(lambda: self.select_output_file(self.output_path))  # 明确传递参数
        
        # 布局设置
        grid.addWidget(img_label, 0, 0)
        grid.addWidget(self.img_path, 0, 1)
        grid.addWidget(img_btn, 0, 2)
        
        grid.addWidget(landuse_label, 1, 0)
        grid.addWidget(self.land_use_path, 1, 1)
        grid.addWidget(landuse_btn, 1, 2)  # 新增行
        
        grid.addWidget(output_label, 2, 0)
        grid.addWidget(self.output_path, 2, 1)
        grid.addWidget(output_btn, 2, 2)
        
        file_group.setLayout(grid)
        layout.addWidget(file_group)

    # 新增土地利用文件选择方法
    def select_land_use_file(self, entry=None):
        """土地利用数据选择方法（全新实现）"""
        if entry is None:
            entry = self.land_use_path        
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择土地利用数据", 
            "", 
            "GeoTIFF文件 (*.tif *.tiff);;所有文件 (*)"
        )
        if path:
            self.land_use_path.setText(path)
            self.update_landuse_values()  # 触发数值更新
            self.check_geo_consistency()  # 触发地理检查
        
    def create_param_group(self, layout):
        """创建参数设置分组"""
        param_group = QGroupBox("参数设置")
        # 参数设置组样式
        param_group = QGroupBox("参数设置")
        param_group.setStyleSheet("""
            QGroupBox {
                font: bold 20px '微软雅黑';
                color: #2C3E50;
                margin-top: 15px;
                padding-top: 25px;
            }
        """)

        grid = QGridLayout()
        
        # 参数列表
        params = [
            ("近红外波段号 (nir_band):", 'nir_band', 0),
            ("红波段号 (red_band):", 'red_band', 1),
            ("SWIR3波段号 (swir3_band):", 'swir3_band', 2),
            ("SWIR2波段号 (swir2_band):", 'swir2_band', 3),
            ("林地像元值 (forst_value):", 'forst_value', 4)
        ]
        
        self.param_entries = {}
        for label, name, row in params:
            lbl = QLabel(label)
            if name == 'forst_value':
                entry = QComboBox()
                entry.setEditable(True)
            else:
                entry = QLineEdit()
                entry.setValidator(QIntValidator(1, 99))
            grid.addWidget(lbl, row, 0)
            grid.addWidget(entry, row, 1)
            self.param_entries[name] = entry
        
        param_group.setLayout(grid)
        layout.addWidget(param_group)
        
    def create_band_info_label(self, layout):
        """创建波段信息显示标签"""
        self.band_info_label = QLabel()
        self.band_info_label.setWordWrap(True)
        self.band_info_label.setStyleSheet("color: #666; font-size: 30px;")
        layout.addWidget(self.band_info_label)
        
    def create_run_button(self, layout):
        """创建运行按钮"""
        btn = QPushButton("执行解混")
        btn.clicked.connect(self.run_unmixing)
        btn.setFixedSize(200, 60)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        
    def create_file_input(self, layout, label, row, is_output=False):
        """创建文件输入行"""
        lbl = QLabel(label)
        entry = QLineEdit()
        btn = QPushButton("浏览...")
        
        if is_output:
            btn.clicked.connect(lambda: self.select_output_file(entry))
        else:
            btn.clicked.connect(lambda: self.select_input_file(entry))
        
        layout.addWidget(lbl, row, 0)
        layout.addWidget(entry, row, 1)
        layout.addWidget(btn, row, 2)
        return entry
        
    def select_input_file(self, entry):
        if entry is None:  # 添加默认参数处理
            entry = self.img_path  # 默认使用影像路径输入框        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "GeoTIFF文件 (*.tif)"
        )
        if file_path:
            try:
                entry.setText(file_path)
                self.display_band_info(file_path)  # 新增信息显示              
                
            except Exception as e:
                self.info_text.appendPlainText(f"⚠️ 文件加载异常: {str(e)}")
            
    def select_output_file(self, entry=None):
        if entry is None:  # 添加默认参数处理
            entry = self.output_path  # 默认使用输出路径输入框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", "", "GeoTIFF文件 (*.tif)"
        )
        if file_path:
            entry.setText(file_path)
            
    def update_band_info(self):
        """更新波段信息提示"""
        path = self.img_path.text()
        if not path: return
        
        try:
            ds = gdal.Open(path)
            if not ds: return
            
            info = []
            for i in range(1, ds.RasterCount + 1):
                band = ds.GetRasterBand(i)
                desc = band.GetDescription() or f"波段{i}"
                info.append(f"{i}: {desc}")
                
            self.band_info_label.setText("影像波段信息:\n" + "\n".join(info))
        except Exception as e:
            self.band_info_label.setText(f"错误: {str(e)}")
            
    def update_landuse_values(self):
        """更新土地利用值选项"""
        path = self.land_use_path.text()
        if not path: return
        
        try:
            values = get_unique_values(path)
            combo = self.param_entries['forst_value']
            combo.clear()
            combo.addItems(map(str, values))
        except Exception as e:
            QMessageBox.warning(self, "警告", f"读取土地利用文件失败:\n{str(e)}")
            
    def run_unmixing(self):
        try:
            # 参数收集（保持forst_value为字符串）
            params = {
                "input_path": self.img_path.text(),
                "land_use_path": self.land_use_path.text(),
                "output_path": self.output_path.text(),
                "nir_band": int(self.param_entries['nir_band'].text()),
                "red_band": int(self.param_entries['red_band'].text()),
                "swir3_band": int(self.param_entries['swir3_band'].text()),
                "swir2_band": int(self.param_entries['swir2_band'].text()),
                "forst_value": str(self.param_entries['forst_value'].currentText())  # 明确保持为字符串
            }

            # 参数验证（新增forst_value特殊校验）
            if not params['forst_value'].isdigit():
                raise ValueError("林地像元值必须为数字字符串，如'1'或'255'")
            
            # 移除原有的int转换
            # params['forst_value'] = int(params['forst_value'])  # 删除此行

            execute_unmixing_with_landuse(**params)
            QMessageBox.information(self, "完成", "解混处理已完成！")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理失败:\n{str(e)}")


    # 新增方法：地理一致性检查
    def check_geo_consistency(self):
        """检查遥感影像与土地利用数据的坐标系和范围一致性"""
        img_path = self.img_path.text()
        lu_path = self.land_use_path.text()
        
        if not img_path or not lu_path:
            return
        
        try:
            # 获取影像空间参考
            img_ds = gdal.Open(img_path)
            img_proj = img_ds.GetProjection()
            img_gt = img_ds.GetGeoTransform()
            img_xsize = img_ds.RasterXSize
            img_ysize = img_ds.RasterYSize
            img_extent = self.calculate_extent(img_gt, img_xsize, img_ysize)
            
            # 获取土地利用数据空间参考
            lu_ds = gdal.Open(lu_path)
            lu_proj = lu_ds.GetProjection()
            lu_gt = lu_ds.GetGeoTransform()
            lu_xsize = lu_ds.RasterXSize
            lu_ysize = lu_ds.RasterYSize
            lu_extent = self.calculate_extent(lu_gt, lu_xsize, lu_ysize)
            
            # 坐标系对比
            srs_img = osr.SpatialReference(wkt=img_proj)
            srs_lu = osr.SpatialReference(wkt=lu_proj)
            
            if not srs_img.IsSame(srs_lu):
                self.info_text.appendPlainText("坐标系不一致！请检查输入数据")
                return
            
            # 范围对比（允许1个像元误差）
            tolerance = max(img_gt[1], abs(img_gt[5]))
            x_match = abs(img_extent[0]-lu_extent[0]) <= tolerance and \
                     abs(img_extent[2]-lu_extent[2]) <= tolerance
            y_match = abs(img_extent[1]-lu_extent[1]) <= tolerance and \
                     abs(img_extent[3]-lu_extent[3]) <= tolerance
            
            if x_match and y_match:
                self.info_text.appendPlainText("地理坐标系和范围一致")
            else:
                self.info_text.appendPlainText("警告：数据范围不一致！")
            
            img_ds = lu_ds = None
            
        except Exception as e:
            self.info_text.appendPlainText(f"地理检查错误：{str(e)}")

    # 新增辅助方法：计算地理范围
    def calculate_extent(self, gt, cols, rows):
        """根据地理变换参数计算四至范围"""
        x_min = gt[0]
        y_max = gt[3]
        x_max = gt[0] + cols * gt[1] + rows * gt[2]
        y_min = gt[3] + cols * gt[4] + rows * gt[5]
        return (x_min, y_max, x_max, y_min)

    # 在GUI类中添加以下方法
    def display_band_info(self, file_path):
        """显示波段信息到反馈面板"""
        try:
            # 清空旧内容
            self.info_text.clear()
            
            # 添加进度提示
            self.info_text.appendPlainText("🔄 正在读取影像元数据...")
            QApplication.processEvents()  # 强制界面刷新
            
            # 获取波段信息
            band_info = self.get_band_names(file_path)
            
            # 构建显示内容
            info_msg = "📡 影像波段信息（名称/描述）：\n"
            for idx, (name, dtype) in enumerate(band_info, 1):
                info_msg += f"波段 {idx}: {name} ({dtype})\n"
                
            # 显示结果
            self.info_text.appendPlainText(info_msg)
            self.info_text.appendPlainText("✅ 元数据读取完成")
            
        except Exception as e:
            error_msg = f"❌ 错误：{str(e)}"
            self.info_text.appendPlainText(error_msg)
            QMessageBox.critical(self, "元数据错误", error_msg)

    def get_band_names(self, file_path):
        """使用GDAL获取波段名称和数据类型"""
        from osgeo import gdal
        band_info = []
        
        try:
            dataset = gdal.Open(file_path)
            if not dataset:
                raise ValueError("无法打开影像文件")
                
            # 获取影像基本信息
            num_bands = dataset.RasterCount
            if num_bands == 0:
                raise ValueError("影像不包含任何波段数据")
            
            # 遍历所有波段
            for i in range(1, num_bands+1):
                band = dataset.GetRasterBand(i)
                
                # 获取波段名称（优先顺序：描述信息 -> 元数据 -> 默认名称）
                name = band.GetDescription() or \
                    band.GetMetadataItem('BandName') or \
                    f"Band {i}"
                    
                # 获取数据类型
                dtype = gdal.GetDataTypeName(band.DataType)
                
                band_info.append((name, dtype))
                
            return band_info
            
        finally:
            # 确保释放资源
            if 'dataset' in locals():
                del dataset