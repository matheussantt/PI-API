
from flask import Flask, request, jsonify
import sqlite3
import hashlib
from ia import get_warranty_claims_ia, gerar_grafico_marcas, gerar_grafico_retornos_mensais, fitness_function, gerar_grafico_retornos_mensais_pecas, gerar_grafico_pecas, get_part_register_list_ia  # Importando as funções de ia.py
from flask_cors import CORS

# Inicialize o app Flask
app = Flask(__name__)

CORS(app)


def connect_db():
    db = sqlite3.connect('database.db')
    # Permite que os resultados sejam acessados como dicionários
    db.row_factory = sqlite3.Row
    return db


def get_part_register_part(partNumber):
    # Conecta ao banco de dados
    db = connect_db()
    cursor = db.cursor()

    # Executa a consulta para obter informações da peça
    cursor.execute('SELECT 1 FROM carPart WHERE partNumber = ?', (partNumber,))
    result = cursor.fetchone()  # Obtém a primeira linha do resultado

    db.close()

    return result is not None  # Retorna True se a peça existe, False caso contrário


def get_part_register_sale(partNumber):
    # Conecta ao banco de dados
    db = connect_db()
    cursor = db.cursor()

    # Executa a consulta para obter informações da peça
    cursor.execute('SELECT 1 FROM carPart WHERE partNumber = ?', (partNumber,))
    result = cursor.fetchone()  # Obtém a primeira linha do resultado

    db.close()

    # Se o resultado for None, significa que a peça não existe, e deve gerar um erro
    if result is None:
        return True  # A peça não existe
    else:
        return False  # A peça já está registrada


def get_warranty_claim_id(partNumber):
    # Conecta ao banco de dados
    db = connect_db()
    cursor = db.cursor()

    # Executa a consulta para obter informações da peça
    cursor.execute(
        'SELECT 1 FROM warrantysClaims WHERE partNumber = ?', (partNumber,))
    result = cursor.fetchone()  # Obtém a primeira linha do resultado

    db.close()

    # Se o resultado for None, significa que a peça não existe, e deve gerar um erro
    if result is None:
        return False  # A peça não existe
    else:
        return True  # A peça já está registrada

# ============================================================================================


@app.route('/register_part', methods=['POST'])
def register_part():
    data = request.json
    partModel = data.get("partModel")
    partBrand = data.get("partBrand")
    partNumber = data.get("partNumber")
    lotNumber = data.get("lotNumber")
    urlQrcode = data.get("urlQrcode")

    # Verificar se todos os campos necessários estão presentes
    required_fields = ['partModel', 'partBrand',
                       'partNumber', 'lotNumber', 'urlQrcode']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"Campo {field} ausente"}), 400

    if get_part_register_part(partNumber):
        return jsonify({"message": "A peça já está cadastrada"}), 400

    # Insere os dados na tabela do banco de dados
    db = connect_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO carPart (partNumber, partModel, partBrand, lotNumber, urlQrcode) VALUES (?, ?, ?, ?, ?)',
                   (partNumber, partModel, partBrand, lotNumber, urlQrcode))
    db.commit()
    db.close()

    return jsonify({"message": "Cadastro realizado com sucesso"}), 200

# Rota para cadastrar uma venda


@app.route('/register_sale', methods=['POST'])
def register_sale():
    data = request.json
    name = data.get("name")
    taxNumber = data.get("taxNumber")
    email = data.get("email")
    phone = data.get("phone")
    partNumber = data.get("partNumber")
    warrantyDeadline = data.get("warrantyDeadline")
    created_at = data.get("created_at")

    # Verificar se todos os campos necessários estão presentes
    required_fields = ['name', 'taxNumber', 'email', 'phone',
                       'partNumber', 'warrantyDeadline', 'created_at']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"Campo {field} ausente"}), 400

    if get_part_register_sale(partNumber):
        return jsonify({"message": "A peça não existe"}), 400

    if created_at > warrantyDeadline:
        return jsonify({"message": "A data de garantia deve ser maior que o dia atual"}), 400

    # Insere os dados na tabela do banco de dados
    db = connect_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT 1 FROM registerSale WHERE partNumber = ?', (partNumber,))
    result = cursor.fetchone()

    if result is not None:
        return jsonify({"message": "A peça já foi vendida"}), 400

    cursor.execute('INSERT INTO registerSale (name, taxNumber, email, phone, partNumber, warrantyDeadline, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (name, taxNumber, email, phone, partNumber, warrantyDeadline, created_at))
    db.commit()
    db.close()

    return jsonify({"message": "Venda cadastrada com sucesso"}), 200

# Rota para verificar se o cliente existe e solicitar a garantia


@app.route('/warranty_claim', methods=['POST'])
def warranty_claim():
    data = request.json
    name = data.get("name")
    taxNumber = data.get("taxNumber")
    email = data.get("email")
    phone = data.get("phone")
    partNumber = data.get("partNumber")

    # Verificar se todos os campos necessários estão presentes
    required_fields = ['name', 'taxNumber', 'email', 'phone', 'partNumber']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"message": f"Campos ausentes: {', '.join(missing_fields)}"}), 400

    if get_warranty_claim_id(partNumber):
        return jsonify({"message": "Já foi solicitada a garantia para peça"}), 400

    # Conectar ao banco e realizar a consulta
    db = connect_db()
    cursor = db.cursor()

    try:
        cursor.execute('''
            SELECT P.partModel, P.partBrand, P.partNumber, P.lotNumber,
                   S.name, S.taxNumber, S.email, S.phone, S.warrantyDeadline
            FROM carPart AS P
            INNER JOIN registerSale AS S ON P.partNumber = S.partNumber
            WHERE P.partNumber = ?
        ''', (partNumber,))

        result = cursor.fetchone()

        if result:
            # Mapeia os resultados retornados pelo banco de dados para um dicionário
            response = {
                "partModel": result[0],
                "partBrand": result[1],
                "partNumber": result[2],
                "lotNumber": result[3],
                "name": result[4],
                "taxNumber": result[5],
                "email": result[6],
                "phone": result[7],
                "warrantyDeadline": result[8]
            }

            # Verificar se os dados batem
            if (response['name'] != name or response['taxNumber'] != taxNumber or
                    response['email'] != email or response['phone'] != phone):
                return jsonify({"message": "Os dados não batem com a venda da peça"}), 404

            # Verificar validade da garantia
            from datetime import datetime
            warranty_deadline = datetime.strptime(
                response['warrantyDeadline'], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > warranty_deadline:
                return jsonify({"message": "A garantia expirou"}), 400

        # Inserir solicitação de garantia
        cursor.execute(
            'INSERT INTO warrantysClaims (partNumber) VALUES (?)', (partNumber,))
        db.commit()
    finally:
        db.close()

    return jsonify({"message": "Garantia solicitada com sucesso"}), 200


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    db = connect_db()
    cursor = db.cursor()

    cursor.execute('SELECT * FROM adminUser WHERE email = ?', (email,))
    result = cursor.fetchone()

    if result == None:
        return jsonify({"message": "email não cadastrado"}), 400

    email_db = result[1]
    password_db = result[2]
    password_md5 = hashlib.md5(password.encode()).hexdigest()

    db.close()

    if password_db == password_md5:
        return jsonify({"message": "Login realizado com sucesso"}), 200
    else:
        return jsonify({"message": "Login não realizado, verifique suas credenciais"}), 400


@app.route('/register', methods=['POST'])
def login_register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    password_md5 = hashlib.md5(password.encode()).hexdigest()

    db = connect_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO adminUser (email, password) VALUES (?, ?)', (email, password_md5))
    db.commit()
    db.close()

    return jsonify({"message": "Registro concluído"}), 200


@app.route('/carpart-info/<partNumber>', methods=['GET'])
def get_part(partNumber):

    # Conecta ao banco de dados
    db = connect_db()
    cursor = db.cursor()

    # Executa a consulta para obter informações da peça
    cursor.execute(
        'SELECT partModel, partBrand, partNumber, lotNumber, urlQrcode FROM carPart WHERE partNumber = ?', (partNumber,))
    result = cursor.fetchone()  # Obtém a primeira linha do resultado

    db.close()

    if result:
        # Mapeia os resultados retornados pelo banco de dados para um dicionário
        response = {
            "partModel": result[0],
            "partBrand": result[1],
            "partNumber": result[2],
            "lotNumber": result[3],
            "urlQrcode": result[4]
        }
        return jsonify(response), 200
    else:
        # Caso nenhum registro seja encontrado
        return jsonify({"message": "Peça não encontrada"}), 404


@app.route('/part_register_list', methods=['GET'])
def get_part_register_list():

    # Conecta ao banco de dados
    db = connect_db()
    cursor = db.cursor()

    # Executa a consulta para obter todas as peças
    cursor.execute(
        'SELECT partModel, partBrand, partNumber, lotNumber, urlQrcode FROM carPart')
    results = cursor.fetchall()  # Obtém todos os registros

    db.close()

    if results:
        # Mapeia os resultados para uma lista de dicionários
        response = [
            {
                "partModel": row[0],
                "partBrand": row[1],
                "partNumber": row[2],
                "lotNumber": row[3],
                "urlQrcode": row[4]
            }
            for row in results
        ]
        return jsonify(response), 200
    else:
        # Caso nenhum registro seja encontrado
        return jsonify({"message": "Nenhuma peça encontrada"}), 404


@app.route('/warranty_claims', methods=['GET'])
def get_warranty_claims():

    # Conecta ao banco de dados
    db = connect_db()
    cursor = db.cursor()

    query = """
    SELECT 
        wc.id,
        cp.partModel, 
        cp.partBrand, 
        cp.partNumber, 
        cp.lotNumber, 
        rs.name, 
        rs.taxNumber, 
        rs.email, 
        rs.phone, 
        rs.warrantyDeadline
    FROM 
        warrantysClaims wc
    INNER JOIN 
        carPart cp ON wc.partNumber = cp.partNumber
    INNER JOIN 
        registerSale rs ON wc.partNumber = rs.partNumber;
    """
    # Executa a consulta para obter todas as peças
    cursor.execute(query)
    results = cursor.fetchall()  # Obtém todos os registros

    db.close()

    if results:
        # Mapeia os resultados para uma lista de dicionários
        response = [
            {
                "id": row[0],
                "partModel": row[1],
                "partBrand": row[2],
                "partNumber": row[3],
                "lotNumber": row[4],
                "name": row[5],
                "taxNumber": row[6],
                "email": row[7],
                "phone": row[8],
                "warrantyDeadline": row[9]
            }
            for row in results
        ]
        return jsonify(response), 200
    else:
        # Caso nenhum registro seja encontrado
        return jsonify({"message": "Nenhuma peça encontrada"}), 404


@app.route('/warranty_claim/<warranty_claim>', methods=['GET'])
def get_warranty_claim(warranty_claim):

 # Conecta ao banco de dados
    db = connect_db()
    cursor = db.cursor()

    # Executa a consulta para obter informações da peça
    cursor.execute('''
    SELECT P.partModel, P.partBrand, P.partNumber, P.lotNumber,
    S.name, S.taxNumber, S.email, S.phone, S.warrantyDeadline
    FROM carPart AS P
    INNER JOIN registerSale AS S ON P.partNumber = S.partNumber
    WHERE P.partNumber = ?
    ''', (warranty_claim,))
    result = cursor.fetchone()  # Obtém a primeira linha do resultado

    db.close()

    if result:
        # Mapeia os resultados retornados pelo banco de dados para um dicionário
        response = {
            "partModel": result[0],
            "partBrand": result[1],
            "partNumber": result[2],
            "lotNumber": result[3],
            "name": result[4],
            "taxNumber": result[5],
            "email": result[6],
            "phone": result[7],
            "warrantyDeadline": result[8]
        }
        return jsonify(response), 200
    else:
        # Caso nenhum registro seja encontrado
        return jsonify({"message": "Garantia não encontrada"}), 404


@app.route('/dados', methods=['GET'])
def dados():
    try:
        # Obtém as reclamações de garantia
        warranty_claims = get_warranty_claims_ia()
        part_register_list = get_part_register_list_ia()

        if not warranty_claims:
            return jsonify({"message": "Nenhuma reclamação de garantia encontrada"}), 404

        # Gerar gráficos
        grafico_marcas_base64 = gerar_grafico_marcas(warranty_claims)
        grafico_mensal_marcas_base64 = gerar_grafico_retornos_mensais(
            warranty_claims)
        grafico_pecas_base64 = gerar_grafico_pecas(part_register_list)
        grafico_mensal_pecas_base64 = gerar_grafico_retornos_mensais_pecas(
            part_register_list)

        # Executa a função fitness e gera o relatório
        fitness_score, relatorio = fitness_function(
            objetivo_retorno_min=50, objetivo_retorno_max=80)

        # Retorna os dados em formato JSON
        return jsonify({
            'grafico_marcas_base64': grafico_marcas_base64,
            'grafico_mensal_marcas_base64': grafico_mensal_marcas_base64,
            'grafico_pecas_base64': grafico_pecas_base64,
            'grafico_mensal_pecas_base64': grafico_mensal_pecas_base64,
            'fitness_score': fitness_score,
            'relatorio': relatorio
        })

    except Exception as e:
        return jsonify({"message": f"Ocorreu um erro: {str(e)}"}), 500


# Execute o app
if __name__ == '__main__':
    app.run(debug=True)
