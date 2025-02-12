from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import re
import sqlite3
import json
from bs4 import BeautifulSoup


# Configuración de Beebotte
BEEBOTTE_API_KEY = 'token_9NUH541rDRyorTwP'  # Token de autenticación para Beebotte
BEEBOTTE_CHANNEL = 'paula'  # Canal de Beebotte donde se almacenan los datos
BEEBOTTE_RESOURCE = 'test'  # Recurso específico del canal

# Conexión a SQLite (base de datos local)
def get_db_connection():
    """Establece y retorna una conexión con la base de datos SQLite."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Permite acceder a los resultados como diccionarios
    return conn

app = Flask(__name__)
app.secret_key = 'mti123'  # Clave secreta para gestionar sesiones en Flask

# Ruta principal
@app.route('/')
def index():
    """Página principal del sistema. Muestra un número aleatorio, lo almacena y lo envía a Beebotte."""
    if 'username' in session:  # Verifica si el usuario ha iniciado sesión
        numero = obtener_numero_aleatorio()  # Extraer número aleatorio
        print(f"Número aleatorio: {numero}")
        if numero is not None:
            almacenar_numero(numero)  # Almacena el número en SQLite
            enviar_a_beebotte(numero)  # Enviar el número a Beebotte
        usuario = session['username']  # Recupera el nombre de usuario de la sesión
        grafica_url = obtener_grafica_beebotte()  # URL de la gráfica generada por Beebotte
        return render_template('index.html', numero=numero, usuario=usuario, grafica_url=grafica_url)
    return redirect(url_for('entrada'))  # Si no hay sesión, redirige a inicio de sesión

# Página de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """Página de registro para nuevos usuarios."""
    if request.method == 'POST':  # Maneja el formulario de registro
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        # Aquí se podría agregar lógica para almacenar usuarios en una base de datos
        flash('Usuario registrado con éxito!')  # Muestra un mensaje de éxito
        return redirect(url_for('entrada'))
    return render_template('registro.html')

# Página de inicio de sesión
@app.route('/entrada', methods=['GET', 'POST'])
def entrada():
    """Página de inicio de sesión para usuarios registrados."""
    if request.method == 'POST':  # Maneja el formulario de inicio de sesión
        username = request.form['username']
        password = request.form['password']
        # En un entorno real, aquí se validaría el usuario contra una base de datos
        session['username'] = username  # Guarda el usuario en la sesión
        flash(f'Bienvenido, {username}!')  # Mensaje de bienvenida
        return redirect(url_for('index'))
    return render_template('entrada.html')

# Solicitar un nuevo número
@app.route('/solicitar_numero', methods=['POST'])
def solicitar_numero():
    """Ruta para solicitar un nuevo número aleatorio."""
    numero = obtener_numero_aleatorio()  # Extrae un nuevo número aleatorio
    if numero is not None:
        guardar_numero_local(numero)  # Guarda el número en SQLite
        guardar_numero_beebotte(numero)  # Envia el número a Beebotte
        flash(f'Número {numero} obtenido y almacenado.')  # Notifica el éxito
    else:
        flash('No se pudo obtener un número aleatorio.')  # Notifica el error
    return redirect(url_for('index'))

# Calcular la media de la base de datos local
@app.route('/calcular_media', methods=['POST'])
def calcular_media_local():
    """Calcula la media de los números almacenados en la base de datos SQLite."""
    conn = get_db_connection()
    numeros = conn.execute('SELECT numero FROM numeros').fetchall()  # Recupera todos los números
    conn.close()
    if numeros:
        media = sum([n['numero'] for n in numeros]) / len(numeros)  # Calcula la media
        flash(f'La media de la base de datos local es: {media:.2f}')
    else:
        flash('No hay números en la base de datos local.')  # Notifica si no hay datos
    return redirect(url_for('index'))

# Calcular la media de Beebotte
@app.route('/calcular_media_beebotte', methods=['POST'])
def calcular_media_beebotte():
    """Calcula la media de los números almacenados en Beebotte."""
    numeros = obtener_numeros_beebotte()  # Recupera los números de Beebotte
    if numeros:
        media = sum(numeros) / len(numeros)  # Calcula la media
        flash(f'La media de Beebotte es: {media:.2f}')
    else:
        flash('No hay números en Beebotte.')  # Notifica si no hay datos
    return redirect(url_for('index'))

# Inicializar la base de datos SQLite
def inicializar_base_datos():
    """Crea la tabla 'numeros' en SQLite si no existe."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS numeros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Obtener número aleatorio de la web
def obtener_numero_aleatorio():
    """Obtiene un número aleatorio de la página 'numeroalazar.com.ar'."""
    try:
        response = requests.get('https://www.numeroalazar.com.ar/')
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')  # Parsear el HTML de la página
            numeros = soup.find('div', class_='numero')  # Buscar la clase que contiene el número
            if numeros:
                numeros = numeros.get_text(separator="\n").strip().split("\n")
                numeros = [num.strip() for num in numeros if num.replace(".", "", 1).isdigit()]
                if numeros:
                    numero = int(float(numeros[0]))
                    guardar_numero_local(numero)  # Guarda en SQLite
                    guardar_numero_beebotte(numero)  # Envia a Beebotte
                    print(f"Número: {numero}")  # Log del número obtenido
                    return numero
    except Exception as e:
        print(f"Error al obtener número aleatorio: {e}")  # Log del error
    return None

# Guardar número en SQLite
def guardar_numero_local(numero):
    """Guarda un número en la base de datos SQLite."""
    conn = get_db_connection()
    conn.execute('INSERT INTO numeros (numero) VALUES (?)', (numero,))
    conn.commit()
    conn.close()

# Guardar número en Beebotte
def guardar_numero_beebotte(numero):
    """Envia un número a Beebotte para almacenarlo."""
    url = f'https://api.beebotte.com/v1/data/write/{BEEBOTTE_CHANNEL}/{BEEBOTTE_RESOURCE}'
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Token': BEEBOTTE_API_KEY
    }
    data = {'data': numero}
    requests.post(url, headers=headers, data=json.dumps(data))

# Obtener datos de Beebotte
def obtener_numeros_beebotte():
    """Obtiene todos los números almacenados en Beebotte."""
    url = f'https://api.beebotte.com/v1/data/read/{BEEBOTTE_CHANNEL}/{BEEBOTTE_RESOURCE}'
    headers = {'X-Auth-Token': BEEBOTTE_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        datos = response.json()  # Decodifica los datos JSON
        return [int(item['data']) for item in datos if item['data'].isdigit()]  # Filtra números válidos
    return []

# Función para almacenar el número en la base de datos local
def almacenar_numero(numero):
    """Guarda un número aleatorio en la base de datos local."""
    conn = get_db_connection()
    conn.execute('INSERT INTO numeros (numero) VALUES (?)', (numero,))
    conn.commit()
    conn.close()

# Función para enviar el número a Beebotte
def enviar_a_beebotte(numero):
    """Envía un número a Beebotte utilizando la API."""
    url = "https://api.beebotte.com/v1/data/write/paula/test"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": "iamtkn_cbch4Cn1QEtMDoa0"
    }
    data = {"data": numero}
    try:
        respuesta = requests.post(url, headers=headers, data=json.dumps(data))
        respuesta.raise_for_status()
    except requests.RequestException as e:
        print(f"Error al enviar el número a Beebotte: {e}")  # Log de error

# Función para obtener la URL de la gráfica generada por Beebotte
def obtener_grafica_beebotte():
    """Retorna la URL de la gráfica generada por Beebotte."""
    return "https://beebotte.com/dash/367e1930-e7e7-11ef-b290-139d4cdb095d"  # URL de la gráfica en Beebotte

if __name__ == "__main__":
    inicializar_base_datos()  # Asegura que la base de datos esté lista antes de iniciar
    app.run(host='0.0.0.0', port=5000, debug=True)  # Inicia el servidor Flask

# No he sido capaz de extraer los numeros aleatorios de la pagina proporcionada, por lo que no he podido probar el funcionamiento completo de la aplicación