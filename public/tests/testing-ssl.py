import psycopg2
import os
import ssl

def test_ssl_connection():
    try:
        # Connection using connection string (more reliable method)
        conn_string = (
            "postgresql://mydb:2#HcgPw&oP4Uf01Z@testdb.wadedesignco.com:5432/mydb"
            "?sslmode=verify-full"
        )
        
        # Alternative connection parameters if needed
        conn_params = {
            'dbname': 'mydb',
            'user': 'mydb',
            'password': '2#HcgPw&oP4Uf01Z',
            'host': 'testdb.wadedesignco.com',
            'port': '5432',
            'sslmode': 'verify-full'  # Strictest SSL mode
        }

        # Try connection (using conn_string)
        conn = psycopg2.connect(conn_string)
        
        # Get SSL status
        cursor = conn.cursor()
        cursor.execute("SHOW ssl;")
        ssl_status = cursor.fetchone()[0]
        
        # Get connection info
        print(f"SSL in use: {ssl_status}")
        print(f"SSL cipher: {conn.info.ssl_cipher}")
        print(f"SSL protocol version: {conn.info.protocol_version}")
        
        cursor.close()
        conn.close()
        print("SSL connection test successful!")
        
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {str(e)}")
        print("\nCommon issues:")
        print("- Invalid SSL mode")
        print("- Certificate verification failed")
        print("- Hostname mismatch")
        print("- Permission issues with certificate files")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    test_ssl_connection()
