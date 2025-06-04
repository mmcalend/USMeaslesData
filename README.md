# US Measles Cases Dataset

This repository contains a manually constructed time series of county-level measles cases in the United States, updated daily via automation.

## Data Source

Original case data is extracted from the Center for Health Security’s [CORI Measles Outbreak Response Dashboard](https://cori.centerforhealthsecurity.org/resources/measles-outbreak-response), which publishes case and exposure information via an ArcGIS feature service.

## About This Dataset

The dashboard does not provide a formal time series or case dates. This dataset was created by recording daily snapshots of the public feature layer and manually assigning report dates to each county-level case. Where available, dates were identified through notes or context fields in the raw dataset itself.

This reconstruction enables daily trend analysis, but may not reflect official case report dates or final epidemiological confirmation. Use with care, and cite the original CORI source appropriately.

## Files

- `USMeaslesCases.csv`: Daily case time series by county
- `USMeaslesDeaths.csv`: Manually compiled data on confirmed measles-related deaths

## License

Provided for educational and public health research purposes only. This dataset is unofficial and not endorsed by the data provider.
