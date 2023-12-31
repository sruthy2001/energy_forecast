# -*- coding: utf-8 -*-
"""Energy Consumption by Sectors

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rpl5J8bAZ0yTkQawb35zXuXCoD5gB3JJ

# Import Libraries
"""

# Import necessary libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_squared_error
from math import sqrt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from joblib import dump

"""# Load Datasets"""

# Load your data
dfp_RC = pd.read_excel('Table_3.7a_Petroleum_Consumption___Residential_and_Commercial_Sectors.xlsx')
dfp_I = pd.read_excel('Table_3.7b_Petroleum_Consumption___Industrial_Sector.xlsx')
dfp_TE = pd.read_excel('Table_3.7c_Petroleum_Consumption___Transportation_and_Electric_Power_Sectors.xlsx')
dfp_NG = pd.read_excel('Table_4.3_Natural_Gas_Consumption_by_Sector.xlsx')
dfp_elec = pd.read_excel('Table_7.6_Electricity_End_Use.xlsx')

dfp_RC.head(5)

# Remove the first line
dfp_RC = dfp_RC.drop(dfp_RC.index[0])

dfp_RC.info()

dfp_RC.head()

# Define the paths to the files
files_and_columns = {
    'Table_3.7a_Petroleum_Consumption___Residential_and_Commercial_Sectors.xlsx':['Total Petroleum Consumed by the Residential Sector', 'Total Petroleum Consumed by the Commercial Sector'],
    'Table_3.7b_Petroleum_Consumption___Industrial_Sector.xlsx':['Total Petroleum Consumed by the Industrial Sector'],
    'Table_4.3_Natural_Gas_Consumption_by_Sector.xlsx':['Natural Gas Consumed by the Residential Sector','Natural Gas Consumed by the Commercial Sector', 'Natural Gas Consumed by the Industrial Sector, Total', 'Natural Gas Consumed by the Transportation Sector, Total'],
    'Table_7.6_Electricity_End_Use.xlsx':['Electricity Sales to Ultimate Customers, Residential', 'Electricity Sales to Ultimate Customers, Commercial', 'Electricity Sales to Ultimate Customers, Industrial', 'Electricity Sales to Ultimate Customers, Transportation'],
    'Table_3.7c_Petroleum_Consumption___Transportation_and_Electric_Power_Sectors.xlsx':['Total Petroleum Consumed by the Transportation Sector']
    }

# Load the data and preprocess
def load_and_preprocess_data(file, columns):
    df = pd.read_excel(file)
    # Removing rows in 0 th index
    df = df.drop(df.index[0])
    for column in columns:
        df[column].replace("Not Available", np.nan, inplace=True)
        df[column] = df[column].astype(float)
        df[column].interpolate(method='linear', inplace=True)
    df = df[['Month'] + columns]
    df.set_index('Month', inplace=True)
    return df

"""# EDA"""

# Load and preprocess data for all the files
dataframes = {}

for file_name, cols in files_and_columns.items():
    file_path = f'{file_name}'
    dataframes[file_name] = load_and_preprocess_data(file_path, cols)

# Displaying the first few rows of each dataset
sample_data = {key: df.head() for key, df in dataframes.items()}
sample_data

# Function to perform EDA and generate graphs for a given dataset
def eda_and_graphs(df, title_prefix, unit):
    # Display basic statistics
    stats = df.describe()

    # Time series plot
    plt.figure(figsize=(14, 8))
    for column in df.columns:
        plt.plot(df.index, df[column], label=column)
    plt.title(f"Time Series: {title_prefix}")
    plt.xlabel("Year")
    plt.ylabel(f"Consumption ({unit})")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # Box plots for each column
    plt.figure(figsize=(14, 6))
    df.boxplot()
    plt.title(f"Box Plot: {title_prefix}")
    plt.ylabel(f"Consumption ({unit})")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    return stats

# Perform EDA for the first dataset
title_prefix = "Petroleum Consumption: Residential and Commercial Sectors"
stats_petroleum_res_com = eda_and_graphs(dataframes['Table_3.7a_Petroleum_Consumption___Residential_and_Commercial_Sectors.xlsx'], title_prefix, "Thousand Barrels Per Day")
stats_petroleum_res_com

# Perform EDA for the second dataset
title_prefix = "Petroleum Consumption: Industrial Sector"
stats_petroleum_ind = eda_and_graphs(dataframes['Table_3.7b_Petroleum_Consumption___Industrial_Sector.xlsx'], title_prefix, "Thousand Barrels Per Day")
stats_petroleum_ind

# Perform EDA for the third dataset
title_prefix = "Natural Gas Consumption by Sector"
stats_natural_gas = eda_and_graphs(dataframes['Table_4.3_Natural_Gas_Consumption_by_Sector.xlsx'], title_prefix, "Billion Cubic Feet")
stats_natural_gas

# Perform EDA for the fourth dataset (fifth in the list but we've already done the electricity one)
title_prefix = "Petroleum Consumption: Transportation and Electric Power Sectors"
stats_petroleum_trans = eda_and_graphs(dataframes['Table_3.7c_Petroleum_Consumption___Transportation_and_Electric_Power_Sectors.xlsx'], title_prefix, "Thousand Barrels Per Day")
stats_petroleum_trans

# Perform EDA for the electricity dataset
title_prefix = "Electricity End Use by Sector"
stats_electricity = eda_and_graphs(dataframes['Table_7.6_Electricity_End_Use.xlsx'], title_prefix, 'Million Kilowatthours')
stats_electricity

"""# Model Methods"""

def train_test_split(data, test_size=0.2):
    train_size = int(len(data) * (1 - test_size))
    train, test = data[:train_size], data[train_size:]
    return train, test

def fit_sarima(data, order, seasonal_order, test):
    model = SARIMAX(data, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
    model_fit = model.fit(disp=False)
    forecast = model_fit.predict(start=len(data), end=len(data)+len(test)-1)
    return model_fit, forecast

def create_lagged_features(data, lag=1):
    if isinstance(data, pd.Series):
        data = data.to_frame()
    lagged_data = data.copy()
    lagged_columns = [f"{column}_lag{lag}" for column in lagged_data.columns]
    lagged_data[lagged_columns] = lagged_data[lagged_data.columns].shift(lag)
    lagged_data.dropna(inplace=True)
    return lagged_data

"""# Training Model"""

# Load the data and preprocess
datasets = {file: load_and_preprocess_data(file, columns) for file, columns in files_and_columns.items()}

import warnings
warnings.filterwarnings('ignore')

# Split the data into training and testing sets
train_datasets = {file: train_test_split(data)[0] for file, data in datasets.items()}
test_datasets = {file: train_test_split(data)[1] for file, data in datasets.items()}

"""To find the best parameters to FIT SARIMA using AIC"""

import itertools
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Continue with the SARIMA grid search for the specified data
data = train_datasets['Table_3.7a_Petroleum_Consumption___Residential_and_Commercial_Sectors.xlsx']['Total Petroleum Consumed by the Residential Sector']

## To find the best paramters to fit SARIMA
# Define the p, d, q and P, D, Q ranges
p = d = q = range(0, 3)  # for non-seasonal orders
P = D = Q = range(0, 2)  # for seasonal orders
s = 12  # for monthly data with yearly seasonality

# Create a list of all possible combinations of p, d, q, P, D, Q, and s
pdq_combinations = [(x[0], x[1], x[2], x[3], x[4], x[5], s) for x in list(itertools.product(p, d, q, P, D, Q))]


best_aic = float("inf")
best_order = None
best_seasonal_order = None

# Grid search for the best SARIMA parameters
for order in pdq_combinations:
    try:
        model = SARIMAX(data, order=(order[0], order[1], order[2]), seasonal_order=(order[3], order[4], order[5], order[6]), enforce_stationarity=False, enforce_invertibility=False)
        results = model.fit()
        if results.aic < best_aic:
            best_aic = results.aic
            best_order = order[0], order[1], order[2]
            best_seasonal_order = order[3], order[4], order[5], order[6]
    except:
        continue

best_order, best_seasonal_order, best_aic

import itertools
from statsmodels.tsa.statespace.sarimax import SARIMAX


## To find the best paramters to fit SARIMA
# Define the p, d, q and P, D, Q ranges
p = d = q = range(0, 3)  # for non-seasonal orders
P = D = Q = range(0, 2)  # for seasonal orders
s = 12  # for monthly data with yearly seasonality

# Create a list of all possible combinations of p, d, q, P, D, Q, and s
pdq_combinations = [(x[0], x[1], x[2], x[3], x[4], x[5], s) for x in list(itertools.product(p, d, q, P, D, Q))]

# Function to determine the best SARIMA parameters based on AIC
def best_sarima_params(data):
    best_aic = float("inf")
    best_order = None
    best_seasonal_order = None

    for order in pdq_combinations:
        try:
            model = SARIMAX(data, order=(order[0], order[1], order[2]), seasonal_order=(order[3], order[4], order[5], order[6]), enforce_stationarity=False, enforce_invertibility=False)
            results = model.fit()
            if results.aic < best_aic:
                best_aic = results.aic
                best_order = order[0], order[1], order[2]
                best_seasonal_order = order[3], order[4], order[5], order[6]
        except:
            continue

    return best_order, best_seasonal_order, best_aic

# Determine the best SARIMA parameters for multiple datasets
results = {}
for file, columns in files_and_columns.items():
    results[file] = {}
    for column in columns:
        data = datasets[file][column]
        order, seasonal_order, aic = best_sarima_params(data)
        results[file][column] = {
            'order': order,
            'seasonal_order': seasonal_order,
            'aic': aic
        }

print(results)

# Fit a SARIMA model and make predictions
sarima_models = {}
sarima_predictions = {}
for file, train_data in train_datasets.items():
    sarima_models[file] = {}
    sarima_predictions[file] = {}
    for column in train_data.columns:
        test_data = test_datasets[file][column]
        sarima_model, sarima_preds = fit_sarima(train_data[column], (2, 1, 2), (1, 1, 1, 12), test_data)
        sarima_models[file][column] = sarima_model
        sarima_predictions[file][column] = sarima_preds

# Create lagged features and fit a Gradient Boosting model
gb_models = {}
gb_predictions = {}
for file, train_data in train_datasets.items():
    gb_models[file] = {}
    gb_predictions[file] = {}
    for column in train_data.columns:
        test_data = test_datasets[file][column]
        lagged_data = create_lagged_features(pd.concat([train_data[column], test_data]))
        X_train, y_train = lagged_data.drop(column, axis=1)[:len(train_data)-1], lagged_data[column][:len(train_data)-1]
        X_test, y_test = lagged_data.drop(column, axis=1)[len(train_data)-1:], lagged_data[column][len(train_data)-1:]
        gb = GradientBoostingRegressor(random_state=42)
        gb.fit(X_train, y_train)
        gb_preds = gb.predict(X_test)
        gb_models[file][column] = gb
        gb_predictions[file][column] = gb_preds

# Combine the SARIMA and Gradient Boosting predictions using a Linear Regression model
stacked_models = {}
stacked_predictions = {}
for file in files_and_columns.keys():
    stacked_models[file] = {}
    stacked_predictions[file] = {}
    for column in train_datasets[file].columns:
        lr = LinearRegression()
        lr.fit(pd.DataFrame({'sarima': sarima_predictions[file][column], 'gb': gb_predictions[file][column]}), test_datasets[file][column])
        stacked_preds = lr.predict(pd.DataFrame({'sarima': sarima_predictions[file][column], 'gb': gb_predictions[file][column]}))
        stacked_models[file][column] = lr
        stacked_predictions[file][column] = stacked_preds

"""# Predictions and Validations"""

# Print and plot the stacked predictions
for file, preds in stacked_predictions.items():
    for column, pred in preds.items():
        print(f"{file} - {column}: {pred}")
        plt.figure(figsize=(14, 6))
        plt.plot(test_datasets[file].index, test_datasets[file][column], label='True Values', color='blue')
        pred_series = pd.Series(pred, index=test_datasets[file].index)
        plt.plot(pred_series.index, pred_series, label='Predictions', color='red')
        plt.title(f"{file} - {column}")
        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.legend()
        plt.show()

"""# Evaluation"""

# Calculate the RMSE and MAPE for the predictions
def calculate_rmse(true_values, predictions):
    mse = mean_squared_error(true_values, predictions)
    rmse = np.sqrt(mse)
    return rmse

def calculate_mape(true_values, predictions):
    mape = np.mean(np.abs((true_values - predictions) / true_values)) * 100
    return mape

# Evaluating SARIMA and GB models
evaluation_results = {}

for file in files_and_columns.keys():
    evaluation_results[file] = {}
    for column in train_datasets[file].columns:
        # Extracting predictions and true values
        sarima_pred = sarima_predictions[file][column]
        gb_pred = gb_predictions[file][column]
        true_values = test_datasets[file][column]

        # Calculating RMSE and MAPE
        sarima_rmse = calculate_rmse(true_values, sarima_pred)
        sarima_mape = calculate_mape(true_values, sarima_pred)

        gb_rmse = calculate_rmse(true_values, gb_pred)
        gb_mape = calculate_mape(true_values, gb_pred)

        # Storing results
        evaluation_results[file][column] = {
            'SARIMA_RMSE': sarima_rmse,
            'SARIMA_MAPE': sarima_mape,
            'GB_RMSE': gb_rmse,
            'GB_MAPE': gb_mape
        }

# Evaluating the stacked model
stacked_evaluation_results = {}

for file in files_and_columns.keys():
    stacked_evaluation_results[file] = {}
    for column in train_datasets[file].columns:
        # Extracting predictions and true values
        stacked_pred = stacked_predictions[file][column]
        true_values = test_datasets[file][column]

        # Calculating RMSE and MAPE
        stacked_rmse = calculate_rmse(true_values, stacked_pred)
        stacked_mape = calculate_mape(true_values, stacked_pred)

        # Storing results
        stacked_evaluation_results[file][column] = {
            'Stacked_RMSE': stacked_rmse,
            'Stacked_MAPE': stacked_mape
        }

"""# Comparison"""

# Incorporating the stacked model results into the previous evaluation results for comparison

for file in files_and_columns.keys():
    for column in train_datasets[file].columns:
        evaluation_results[file][column]['Stacked_RMSE'] = stacked_evaluation_results[file][column]['Stacked_RMSE']
        evaluation_results[file][column]['Stacked_MAPE'] = stacked_evaluation_results[file][column]['Stacked_MAPE']

# Return the combined evaluation results
evaluation_results

from sklearn.metrics import mean_absolute_error, r2_score

# Calculating additional evaluation metrics
evaluation_additional_metrics = {}

for file in files_and_columns.keys():
    evaluation_additional_metrics[file] = {}
    for column in train_datasets[file].columns:
        # Extracting predictions and true values
        sarima_pred = sarima_predictions[file][column]
        gb_pred = gb_predictions[file][column]
        stacked_pred = stacked_predictions[file][column]
        true_values = test_datasets[file][column]

        # Calculating MAE and R2 for each model
        sarima_mae = mean_absolute_error(true_values, sarima_pred)
        sarima_r2 = r2_score(true_values, sarima_pred)

        gb_mae = mean_absolute_error(true_values, gb_pred)
        gb_r2 = r2_score(true_values, gb_pred)

        stacked_mae = mean_absolute_error(true_values, stacked_pred)
        stacked_r2 = r2_score(true_values, stacked_pred)

        # Storing results
        evaluation_additional_metrics[file][column] = {
            'SARIMA_MAE': sarima_mae,
            'SARIMA_R2': sarima_r2,
            'GB_MAE': gb_mae,
            'GB_R2': gb_r2,
            'Stacked_MAE': stacked_mae,
            'Stacked_R2': stacked_r2
        }

# Generating Residual Plots
residual_plots = {}
for file in files_and_columns.keys():
    residual_plots[file] = {}
    for column in train_datasets[file].columns:
        plt.figure(figsize=(14, 6))

        # Calculating residuals
        sarima_residuals = test_datasets[file][column] - sarima_predictions[file][column]
        gb_residuals = test_datasets[file][column] - gb_predictions[file][column]
        stacked_residuals = test_datasets[file][column] - stacked_predictions[file][column]

        # Plotting residuals
        plt.plot(test_datasets[file].index, sarima_residuals, label='SARIMA Residuals', color='blue')
        plt.plot(test_datasets[file].index, gb_residuals, label='GB Residuals', color='red')
        plt.plot(test_datasets[file].index, stacked_residuals, label='Stacked Residuals', color='green')

        plt.title(f"Residuals for {file} - {column}")
        plt.xlabel('Time')
        plt.ylabel('Residual Value')
        plt.legend()
        plt.show()

# Return the additional evaluation metrics
evaluation_additional_metrics

"""# GB, SARIMA, Stacked"""

# Plotting SARIMA, GB, Stacked predictions along with true labels for visualization

for file in files_and_columns.keys():
    for column in train_datasets[file].columns:

        # Extracting true values and predictions
        true_values = test_datasets[file][column]
        sarima_pred = sarima_predictions[file][column]
        gb_pred = gb_predictions[file][column]
        stacked_pred = stacked_predictions[file][column]

        plt.figure(figsize=(16, 8))

        # Plotting true values and predictions
        plt.plot(true_values.index, true_values, label='True Values', color='black', linestyle='--', linewidth=1.5)
        plt.plot(true_values.index, sarima_pred, label='SARIMA Predictions', color='blue')
        plt.plot(true_values.index, gb_pred, label='GB Predictions', color='red')
        plt.plot(true_values.index, stacked_pred, label='Stacked Predictions', color='green')

        plt.title(f"Predictions vs True Values for {file} - {column}")
        plt.xlabel('Time')
        plt.ylabel('Value')
        plt.legend()
        plt.grid(True)
        plt.show()



"""# Next 5 Years"""

# Adjust the generate_forecast function to handle iterative forecasting correctly

def generate_forecast(model, sarima_predictions, gb_model, forecast_length):
    # Generate initial forecasts using SARIMA
    sarima_forecast = model.forecast(steps=forecast_length)

    # For GB we need to iteratively predict and use the last prediction as a new input
    gb_forecast = []
    last_observation = sarima_predictions.iloc[-1]
    for _ in range(forecast_length):
        new_prediction = gb_model.predict(np.array([last_observation]).reshape(1, -1))
        gb_forecast.append(new_prediction[0])
        last_observation = new_prediction

    # Use the linear regression model to combine the forecasts
    stacked_forecast = lr.predict(pd.DataFrame({'sarima': sarima_forecast, 'gb': gb_forecast}))
    return stacked_forecast

# Define the number of months to forecast
forecast_length = 108  # 9 years * 12 months

# Regenerate forecasts
forecasts = {}
for file in files_and_columns.keys():
    forecasts[file] = {}
    for column in train_datasets[file].columns:
        model = sarima_models[file][column]
        gb_model = gb_models[file][column]
        lr = stacked_models[file][column]
        forecast = generate_forecast(model, sarima_predictions[file][column], gb_model, forecast_length)
        forecasts[file][column] = forecast

# Display the forecasts for the first file and column as an example again
example_file = list(files_and_columns.keys())[0]
example_column = files_and_columns[example_file][0]
forecasts[example_file][example_column]

# Generate the date range for the forecasts
forecast_dates = pd.date_range(start="2020-01-01", periods=forecast_length, freq='M')

import matplotlib.pyplot as plt

# Extract true values from 2020 onwards from the test dataset
true_values_2020_onwards = test_datasets[example_file][example_column]

# Compute the confidence intervals for SARIMA predictions
confidence_intervals = sarima_models[example_file][example_column].get_forecast(steps=forecast_length).conf_int()

# Plotting data from 2020 onwards with true values up to 2023
plt.figure(figsize=(14, 7))
# Plotting the true values from 2020 to 2023
plt.plot(true_values_2020_onwards.index, true_values_2020_onwards, label="True Values (2020-2023)", color='blue')
# Plotting forecasted values from 2020 to 2028
plt.plot(forecast_dates, forecasts[example_file][example_column], label="Forecast (2020-2028)", color='red', linestyle='--')
plt.fill_between(forecast_dates, confidence_intervals.iloc[:, 0], confidence_intervals.iloc[:, 1], color='pink', alpha=0.3, label="SARIMA Confidence Interval")
plt.title(f"True Values (2020-2023) vs. Forecasted Values for {example_column}")
plt.xlabel("Date")
plt.ylabel("Value")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

|# Function to plot the data and forecasts for each dataset and column
def plot_true_vs_forecast(file, column):
    # Extract the true values and the forecasted values
    true_values = test_datasets[file][column]
    forecast_vals = forecasts[file][column]
    confidence_intervals = sarima_models[file][column].get_forecast(steps=forecast_length).conf_int()

    # Plotting
    plt.figure(figsize=(14, 7))
    plt.plot(true_values.index, true_values, label="True Values", color='blue')
    plt.plot(forecast_dates, forecast_vals, label="Forecast", color='red', linestyle='--')
    plt.fill_between(forecast_dates, confidence_intervals.iloc[:, 0], confidence_intervals.iloc[:, 1], color='pink', alpha=0.3, label="SARIMA Confidence Interval")
    plt.title(f"True vs. Forecasted Values for {column}")
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Loop through each dataset and column to plot the data and forecasts
for file, columns in files_and_columns.items():
    for column in columns:
        plot_true_vs_forecast(file, column)

"""Key points about confidence intervals:

Confidence Level: This represents the probability that the parameter lies within the CI. Common choices for the confidence level are 90%, 95%, and 99%. For example, a 95% confidence interval means that you can be 95% certain that the interval contains the true population parameter. This is beneficial for risk assessment and decision-making.

Width: A wider interval might increase the confidence that the parameter lies within it but reduces precision. Conversely, a narrower interval might be more precise but less confident.

Interpretation: If you were to repeat a study over and over, then 95% (for a 95% CI) of the calculated intervals would contain the true value. It doesn't mean that there's a 95% chance the specific interval you've calculated contains the true value.

Application in Forecasting: In time series forecasting, like with the SARIMA model, confidence intervals provide a range within which future observations are expected to fall a certain percentage of the time. They account for the uncertainty inherent in predicting the future.

SARIMA forecast analysis graphs for all residential sectors across the datasets. We'll provide insights based on the following categories:

1. **Electricity Consumption - Residential Sector**
2. **Natural Gas Consumption - Residential Sector**
3. **Petroleum Consumption - Residential Sector**

I will be looking at:

- The forecast trend.
- Points of significant increase or decrease.
- The width of the confidence intervals.
- Any notable patterns or anomalies.

Let's begin our analysis:

**1. Electricity Consumption - Residential Sector**

- **Trend**: The forecast indicates a generally upward trend in electricity consumption for the residential sector from 2020 to 2028. This suggests an increasing demand for electricity in homes over this period.
- **Points of Significant Change**: There are cyclical patterns evident in the forecast, where peaks and troughs occur annually. The peaks, which represent higher electricity consumption, likely coincide with periods of higher energy use, such as winter or summer months when heating or cooling systems are used more intensively.
- **Confidence Interval**: The confidence intervals are relatively narrow, indicating that the model has a strong degree of certainty about its predictions. However, the intervals expand slightly towards the latter years, suggesting increasing uncertainty as we forecast further into the future.
- **Notable Patterns**: The cyclical annual pattern suggests that seasonality plays a significant role in residential electricity consumption.

**2. Natural Gas Consumption - Residential Sector**

- **Trend**: The forecast displays a moderate upward trend in natural gas consumption from 2020 to 2028. This could be attributed to an increasing preference for natural gas as a cleaner fuel or growth in residential areas.
- **Points of Significant Change**: Similar to electricity consumption, there's a clear cyclical pattern in natural gas consumption. Peaks typically represent winter months when natural gas is extensively used for heating.
- **Confidence Interval**: The confidence intervals for this forecast are slightly broader than those for electricity consumption, suggesting a bit more uncertainty in the predictions. However, they're still relatively narrow, indicating a good degree of model confidence.
- **Notable Patterns**: Again, the clear seasonality is evident, reinforcing the idea that natural gas consumption in homes is heavily influenced by seasonal changes.

**3. Petroleum Consumption - Residential Sector**

- **Trend**: The forecast suggests a slight decrease in petroleum consumption for the residential sector from 2020 onwards. This could be due to a shift towards more sustainable energy sources or improved energy efficiency in homes.
- **Points of Significant Change**: Unlike the other energy sources, petroleum consumption doesn't display a strong cyclical pattern, suggesting that its use isn't as influenced by seasonality. However, there are minor fluctuations throughout the years.
- **Confidence Interval**: The confidence intervals are relatively consistent in width over the forecast period, indicating a steady level of uncertainty in the predictions.
- **Notable Patterns**: The absence of a strong seasonal pattern and the overall decline might suggest a decreasing reliance on petroleum as a primary energy source in the residential sector.

**Overall Insights**:

- All three energy sources exhibit distinct patterns of consumption in the residential sector. While electricity and natural gas show strong seasonality, petroleum does not.
- There's a general increase in the consumption of electricity and natural gas, possibly due to growing residential areas or changing consumption habits. In contrast, petroleum sees a decline, indicating potential shifts in energy preferences.
- Confidence intervals across all forecasts are relatively narrow, suggesting that the SARIMA model is fairly confident in its predictions, though there's always inherent uncertainty in any forecast.

# SARIMA 5 Year Forecast
"""

# Function to generate SARIMA forecasts
def generate_sarima_forecast(model, forecast_length):
    forecast = model.get_forecast(steps=forecast_length)
    mean_forecast = forecast.predicted_mean
    confidence_intervals = forecast.conf_int()
    return mean_forecast, confidence_intervals


# Function to plot SARIMA forecasts for each dataset and column
def plot_sarima_forecast(file, column):
    # Extract the true values, the forecasted values, and the confidence intervals
    true_values = test_datasets[file][column]
    forecast_vals = sarima_forecasts[file][column]
    confidence_intervals = sarima_confidence_intervals[file][column]

    # Plotting
    plt.figure(figsize=(14, 7))
    plt.plot(true_values.index, true_values, label="True Values", color='blue')
    plt.plot(forecast_dates, forecast_vals, label="SARIMA Forecast", color='red', linestyle='--')
    plt.fill_between(forecast_dates, confidence_intervals.iloc[:, 0], confidence_intervals.iloc[:, 1], color='pink', alpha=0.3, label="SARIMA Confidence Interval")
    plt.title(f"True vs. SARIMA Forecasted Values for {column}")
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Generate SARIMA forecasts for each dataset and column
sarima_forecasts = {}
sarima_confidence_intervals = {}
for file in files_and_columns.keys():
    sarima_forecasts[file] = {}
    sarima_confidence_intervals[file] = {}
    for column in train_datasets[file].columns:
        model = sarima_models[file][column]
        forecast, conf_int = generate_sarima_forecast(model, forecast_length)
        sarima_forecasts[file][column] = forecast
        sarima_confidence_intervals[file][column] = conf_int

# Loop through each dataset and column to plot the SARIMA forecasts
for file, columns in files_and_columns.items():
    for column in columns:
        plot_sarima_forecast(file, column)

