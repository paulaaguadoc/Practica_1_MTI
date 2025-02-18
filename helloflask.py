from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import re
import sqlite3
import json
from bs4 import BeautifulSoup
from beebotte import BBT

API_KEY = "ndicHZa04aB4O40b7f7X1emy"
SECRET_KEY = "lGfXoYa8P2dZrpMNZvVmRJv9RCuu0Deb"
BEEBOTTE_CHANNEL = 'paula'  # Canal de Beebotte donde se almacenan los datos
BEEBOTTE_RESOURCE = 'numeros'  # Recurso específico del canal

# Contadores globales
media_local_count = 0
media_beebotte_count = 0

# Crear conexión con Beebotte
bbt = BBT(API_KEY, SECRET_KEY)

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
            guardar_numero_beebotte(BEEBOTTE_CHANNEL, BEEBOTTE_RESOURCE,numero)  # Enviar el número a Beebotte
        usuario = session['username']  # Recupera el nombre de usuario de la sesión
        grafica_url = obtener_grafica_beebotte()  # URL de la gráfica generada por BeebotteS
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
        flash('Usuario registrado con éxito!')
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
        guardar_numero_beebotte(BEEBOTTE_CHANNEL, BEEBOTTE_RESOURCE, numero)  # Envia el número a Beebotte
        flash(f'Número {numero} obtenido y almacenado.')  # Notifica el éxito
    else:
        flash('No se pudo obtener un número aleatorio.')  # Notifica el error
    return redirect(url_for('index'))

@app.route('/calcular_media', methods=['POST'])
def calcular_media_local():
    """Calcula la media de los números almacenados en la base de datos SQLite y la muestra en la página."""
    global media_local_count  # Acceder al contador global
    conn = get_db_connection()
    numeros = conn.execute('SELECT numero FROM numeros').fetchall()
    conn.close()

    if numeros:
        valores = [row[0] for row in numeros]  # Extraer correctamente los valores
        media = sum(valores) / len(valores)  # Calcular la media
        media_local_count += 1  # Incrementar el contador de la media local
        return render_template('index.html', media_local=media, media_local_count=media_local_count)  # Enviar el contador a la plantilla
    else:
        return render_template('index.html', media_local="No hay datos disponibles", media_local_count=media_local_count)
    

@app.route('/calcular_media_beebotte', methods=['POST'])
def calcular_media_beebotte():
    """Calcula la media de los números almacenados en Beebotte."""
    global media_beebotte_count  # Acceder al contador global
    numeros = obtener_numeros_beebotte(BEEBOTTE_CHANNEL, BEEBOTTE_RESOURCE)  # Recupera los números de Beebotte
    if numeros:
        media = sum(numeros) / len(numeros)  # Calcula la media
        media_beebotte_count += 1  # Incrementar el contador de la media en Beebotte
        return render_template('index.html', media_bebotte=media, media_beebotte_count=media_beebotte_count)  # Enviar el contador a la plantilla
    else:
        return render_template('index.html', media_bebotte="No hay datos disponibles", media_beebotte_count=media_beebotte_count)

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


def obtener_numero_aleatorio():
    """Obtiene un número aleatorio de la página 'numeroalazar.com.ar' usando expresiones regulares."""
    try:
        response = requests.get('https://www.numeroalazar.com.ar/')
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')  # Analiza el HTML de la página
            texto = soup.get_text()  # Extrae el texto de la página

            # Expresión regular para buscar un número aleatorio en el contenido
            match = re.search(r'\b\d+\b', texto)
            if match:
                numero = int(match.group())  # Convierte el número a entero
                print(f"Número aleatorio obtenido: {numero}")
                return numero
    except Exception as e:
        print(f"Error al obtener número aleatorio: {e}")

    return None  # Devuelve None si no encuentra un número

# Guardar número en SQLite
def guardar_numero_local(numero):
    """Guarda un número en la base de datos SQLite."""
    conn = get_db_connection()
    conn.execute('INSERT INTO numeros (numero) VALUES (?)', (numero,))
    conn.commit()
    conn.close()


# Escribir datos en un canal y recurso específicos
def guardar_numero_beebotte(BEEBOTTE_CHANNEL, BEEBOTTE_RESOURCE, valor):
    try:
        bbt.write(BEEBOTTE_CHANNEL, BEEBOTTE_RESOURCE, valor)
        print(f"Valor '{valor}' almacenado en {BEEBOTTE_CHANNEL}/{BEEBOTTE_RESOURCE}.")
    except Exception as e:
        print(f"Error al escribir en Beebotte: {e}")


def obtener_numeros_beebotte(BEEBOTTE_CHANNEL, BEEBOTTE_RESOURCE):
    record = bbt.read(BEEBOTTE_CHANNEL, BEEBOTTE_RESOURCE, limit=1000)
    if isinstance(record, list):  # Si es una lista, extraer los datos
        return [entry['data'] for entry in record]
    elif isinstance(record, dict):  # Si es un solo dict, envolver en lista
        return [record['data']]
    return []  # Si no hay datos, devolver una lista vacía

# Función para almacenar el número en la base de datos local
def almacenar_numero(numero):
    """Guarda un número aleatorio en la base de datos local."""
    conn = get_db_connection()
    conn.execute('INSERT INTO numeros (numero) VALUES (?)', (numero,))
    conn.commit()
    conn.close()

# Función para obtener la URL de la gráfica generada por Beebotte
def obtener_grafica_beebotte():
    """Retorna la URL de la gráfica generada por Beebotte."""
    return "https://beebotte.com/dash/1bf91e60-edfb-11ef-b290-139d4cdb095d"  # URL de la gráfica en Beebotte

if __name__ == "__main__":
    inicializar_base_datos()  # Asegura que la base de datos esté lista antes de iniciar
    app.run(host='0.0.0.0', port=5000, debug=True)  # Inicia el servidor Flask

