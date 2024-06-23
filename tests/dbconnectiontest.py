import pyodbc

connection_string = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=ne-az-sql-serv1.database.windows.net;'
    'DATABASE=d01jcq35qv74048;'
    'UID=u9chzolmxho9m68;'
    'PWD=0ci@dsWyXcQ3wNr$apemnsLYP;'
    'Encrypt=yes;'
    'TrustServerCertificate=no;'
)

try:
    conn = pyodbc.connect(connection_string)
    print("Connection successful!")
    conn.close()
except pyodbc.Error as e:
    print("Connection failed: ", e)