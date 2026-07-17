# wa_helper.py
import requests
import os

# Idealnya, token ini disimpan di file .env untuk keamanan
WA_API_TOKEN = os.getenv('WA_API_TOKEN', 'token_rahasia_anda_disini')
WA_API_URL = 'https://api.fonnte.com/send' # Contoh endpoint Fonnte

def kirim_whatsapp(nomor_tujuan, pesan):
    """
    Fungsi untuk mengirim pesan WhatsApp menggunakan API Gateway.
    """
    headers = {
        'Authorization': WA_API_TOKEN,
    }
    
    payload = {
        'target': nomor_tujuan,
        'message': pesan,
        'countryCode': '62', # Memaksa format ke kode negara Indonesia
    }
    
    try:
        response = requests.post(WA_API_URL, headers=headers, data=payload)
        response_data = response.json()
        
        if response_data.get('status'):
            print(f"Berhasil mengirim WA ke {nomor_tujuan}")
            return True
        else:
            print(f"Gagal mengirim WA ke {nomor_tujuan}: {response_data.get('reason')}")
            return False
            
    except Exception as e:
        print(f"Error koneksi ke API WhatsApp: {e}")
        return False