import pyodbc
import pandas as pd
import matplotlib.pyplot as plt
 
# DB server credentials
server = 'IP'
database = 'DB'
username = 'username'
password = 'Password'
 
#Defining ODBC connection string
conn_str = f'''
    DRIVER={{ODBC Driver 17 for SQL Server}};
    Server={server};
    DATABASE={database};
    UID={username};
    PWD={password};
    TrustServerCertificate=yes;
'''
# Start and end dates
start_date = 'YYYY-MM-DD'
end_date = 'YYYY-MM-DD'
 
try:
    # DB server connection
    conn = pyodbc.connect(conn_str)
    print("Connected Successfully!")
 
    # SQL query for battery calculations
    sql_query = """
    -- Declare variables for IMEI, TObjectID, and start/end dates
    DECLARE @IMEI AS VARCHAR(MAX) = 'DEVICEIMEI';
    DECLARE @CSLID AS VARCHAR(MAX);
    DECLARE @TObjectId AS VARCHAR(MAX);
   DECLARE @StartDate AS DATE = ?;  -- Specify the starting date
    DECLARE @EndDate AS DATE = ?;  -- Optional end date
 
    -- Retrieve CallSignID and TObjectID
    SET @CSLID = (SELECT ID FROM PTUSER_SkyPatrol.dbo.CallSign_List WHERE IMEI = @IMEI);
    SET @TObjectId = (SELECT ID FROM PTUSER_SkyPatrol.dbo.TObject_List WHERE CallSignID = @CSLID AND IsDeleted = 0);
 
    -- Get the number of days in the timeframe
    DECLARE @DaysCount INT = DATEDIFF(DAY, @StartDate, @EndDate) + 1;
 
    -- Find the first and last recorded max battery voltage within the date range
    DECLARE @StartMaxVoltage FLOAT = (
        SELECT TOP 1 MAX(BatteryVoltage)
        FROM PTUSER_SkyPatrol.dbo.TObject_History
        WHERE TObjectID = @TObjectId
              AND CAST(TrueTime AS DATE) >= @StartDate
        GROUP BY CAST(TrueTime AS DATE)
        ORDER BY CAST(TrueTime AS DATE) ASC
    );
 
    DECLARE @EndMaxVoltage FLOAT = (
        SELECT TOP 1 MAX(BatteryVoltage)
        FROM PTUSER_SkyPatrol.dbo.TObject_History
        WHERE TObjectID = @TObjectId
              AND CAST(TrueTime AS DATE) <= @EndDate
        GROUP BY CAST(TrueTime AS DATE)
        ORDER BY CAST(TrueTime AS DATE) DESC
    );
 
    -- Final selection with average battery drop per day
    SELECT
        CASE
            WHEN @StartMaxVoltage IS NOT NULL AND @EndMaxVoltage IS NOT NULL
            THEN (@StartMaxVoltage - @EndMaxVoltage) / NULLIF(@DaysCount, 0)
            ELSE NULL
        END AS avg_battery_drop_per_day;
    """
 
    # Get the data from SQL and store it in a pandas DataFrame
    df = pd.read_sql(sql_query, conn, params=[start_date, end_date])
    print(df.head())  # Check the results
 
    # Fetch actual battery voltage trends for visualization
    trend_query = """
    SELECT
        CAST(TrueTime AS DATE) AS day,
        MAX(BatteryVoltage) AS BatteryVoltage
    FROM
        PTUSER_SkyPatrol.dbo.TObject_History
    WHERE
        TObjectID = (SELECT ID FROM PTUSER_SkyPatrol.dbo.TObject_List WHERE CallSignID =
                     (SELECT ID FROM PTUSER_SkyPatrol.dbo.CallSign_List WHERE IMEI = ?)
                     AND IsDeleted = 0)
        AND CAST(TrueTime AS DATE) BETWEEN ? AND ?
    GROUP BY
        CAST(TrueTime AS DATE)
    ORDER BY
        day;
    """
 
    df_trend = pd.read_sql(trend_query, conn, params=['DEVICEIMEI', start_date, end_date])
 
    # Plot battery percentage trend over time
    plt.figure(figsize=(10, 6))
    plt.plot(df_trend['day'], df_trend['BatteryVoltage'], label='Battery Percentage', color='g')
 
    # Formatting the plot
    plt.xlabel('Day')
    plt.ylabel('Battery Voltage (V)')
    plt.title('Battery Percentage Trend Over Time')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.legend()
    plt.show()
 
except Exception as e:
    print("Connection Failed", e)
