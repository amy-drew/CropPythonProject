This repository contains Python code and data used to:

+ Predict crop yields using machine‑learning models
+ Analyse environmental and weather features
+ Provide estimated yields for different crops under Low, Medium, and High input conditions
+ Support a simple app/website interface

Main Files

+ Project.py — main script for running predictions
+ CropPrices.xlsx / CropPrices2.xlsx — crop price data
+ EcoCrop_DB.csv — crop suitability dataset
+ FAOSTAT_data_en_8-18-2025.csv — global agricultural data
+ crop_model_Low.h5 / Medium.h5 / High.h5 — trained ML models
+ feature weight files — model interpretability outputs
+ YieldTest.py / YieldTest.md — testing scripts and notes
+ Project.md — project documentation

Running the Project
1. Download all the files
2. intall all dependicies
3. Run the main script
4. launch the app using

		streamlit run Project.py

All datasets used are freely available, including:
+ FAOSTAT
+ EcoCrop
+ Public climate and environmental datasets
