# Vegetation Cover Unmixing Tool (PV/NPV/BS)

This Python-based tool estimates fractional cover of **photosynthetic vegetation (PV)**, **non-photosynthetic vegetation (NPV)**, and **bare soil (BS)** from multispectral remote sensing imagery. It employs a fully constrained linear spectral unmixing method in a two-dimensional spectral space (NDVI and SWIR32), using land cover data to differentiate endmembers for forest and non-forest regions. The tool supports multicore parallel processing and includes a GUI built with PyQt5.

## 🧠 Key Features

- Computes NDVI and SWIR32 indices to construct a 2D spectral space
- Supports land-cover-based endmember selection (forest vs. non-forest)
- Solves constrained unmixing for PV/NPV/BS fractions
- Multicore parallelism (CPU-based; no GPU required)
- Optional graphical user interface (GUI) for non-programmers

## 📥 Inputs

- **Multispectral GeoTIFF image** containing at least the following bands:
  - Red (approx. 620–670 nm)
  - NIR (approx. 841–876 nm)
  - SWIR2 (approx. 1628–1652 nm)
  - SWIR3 (approx. 2105–2155 nm)

- **Land use raster (GeoTIFF)**:
  - Integer values (e.g., 1, 2, 3…)
  - Spatial resolution and projection must match the multispectral image
  - User must provide the integer value(s) representing forest pixels

## 📤 Output

- A 3-band GeoTIFF image:
  - **Band 1**: PV (Photosynthetic Vegetation Fraction)
  - **Band 2**: NPV (Non-Photosynthetic Vegetation Fraction)
  - **Band 3**: BS (Bare Soil Fraction)

## ⚙️ Requirements

- Python ≥ 3.8
- [NumPy](https://numpy.org/)
- [SciPy](https://scipy.org/)
- [GDAL](https://gdal.org/)
- [PyQt5](https://pypi.org/project/PyQt5/) *(GUI only)*

Install dependencies with:

```bash
pip install -r requirements.txt
```

## 🚀 Usage

### 1. Python Script (CLI)

```python
from unmix_with_landuse import execute_unmixing_with_landuse

execute_unmixing_with_landuse(
    input_path="input_image.tif",
    land_use_path="landuse_map.tif",
    output_path="output_fractions.tif",
    nir_band=2,
    red_band=1,
    swir3_band=7,
    swir2_band=6,
    forst_value="3"  # e.g., value representing forest in land use map
)
```

### 2. Graphical User Interface (GUI)

To run the GUI:

```bash
python gui_main.py
```

- Default login: `admin` / `admin`
- Allows selection of input/output files, band numbers, and land cover values

## 📌 Notes

- Band numbers are **1-based** (as used in GDAL)
- The tool uses **half of available CPU threads** by default
- GPU is not required
- Ensure land use raster covers the same extent and uses the same projection as the input image

## 📄 License

This project is released under the [MIT License](LICENSE).

---

If you find this tool useful in your research, please consider citing or starring ⭐ this repository.
