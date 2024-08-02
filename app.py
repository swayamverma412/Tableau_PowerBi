from flask import Flask, request, send_file, jsonify, render_template
import os
import pandas as pd
from graphviz import Digraph
import graphviz
import textwrap
from dotenv import load_dotenv
import google.generativeai as genai
from IPython.display import Markdown

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Function to find potential primary keys in a DataFrame
def find_potential_primary_keys(df):
    potential_primary_keys = []
    for column in df.columns:
        if df[column].nunique() == len(df):
            potential_primary_keys.append(column)
    return potential_primary_keys

def find_potential_primary_keys_id(df):
    return [col for col in df.columns if col.endswith('id')]

# Function to generate the ER diagram as .dot and .png files
def generate_er_diagram():
    try:
        csv_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.csv')]
        dataframes = {}
        primary_keys = {}

        # Read each CSV file into a DataFrame and find potential primary keys
        for file in csv_files:
            df = pd.read_csv(os.path.join(UPLOAD_FOLDER, file))
            dataframes[file] = df
            primary_keys[file] = find_potential_primary_keys(df)

        # Function to check if a DataFrame has any date columns
        def has_date_columns(df):
            date_columns = df.select_dtypes(include=['datetime', 'datetime64', 'timedelta']).columns
            return len(date_columns) > 0

        # Create a Digraph object from graphviz
        dot = Digraph(comment='ER Diagram')

        # Add nodes (tables) and edges (relationships)
        for file in csv_files:
            keys_with_id_suffix = [key for key in primary_keys[file] if key.endswith('id')]
            label = f"{file}\n({', '.join(keys_with_id_suffix)})"
            dot.node(file, label=label, shape='box')

        foreign_keys = {}

        # Find relationships (edges) between tables based on primary keys
        for file, keys in primary_keys.items():
            for key in keys:
                if not key.endswith('id'):
                    continue
                for other_file, other_df in dataframes.items():
                    if file != other_file and key in other_df.columns:
                        dot.edge(file, other_file)
                        if key not in foreign_keys:
                            foreign_keys[key] = []
                        foreign_keys[key].append(other_file)
        print(foreign_keys)
         
        # Dictionary to store table types
        table_types = {}

        # Determine table types
        for file in csv_files:
            if has_date_columns(dataframes[file]):
                table_types[file] = 'Fact'
            else:
                is_fact = True
                for key in primary_keys[file]:
                    if key in foreign_keys:
                        is_fact = False
                        break
                table_types[file] = 'Fact' if is_fact else 'Dimension'

        # Print table types and columns for dimension tables
        dimension_tables = {}
        for file, table_type in table_types.items():
            print(f"Table: {file}")
            print(f"Type: {table_type}")
            if table_type == 'Dimension':
                columns = dataframes[file].columns.tolist()
                dimension_tables[file] = columns
                print(f"Columns: {', '.join(columns)}")
            print("\n")

        fact_tables = {}
        for file, table_type in table_types.items():
            print(f"Table: {file}")
            print(f"Type: {table_type}")
            if table_type == 'Fact':
                columns = dataframes[file].columns.tolist()
                fact_tables[file] = columns
                print(f"Columns: {', '.join(columns)}")
            print("\n")
       
        # Create a graph to represent relationships using Graphviz
        dot = graphviz.Digraph(comment='ER Diagram')

        # Add nodes for each table
        for file in csv_files:
            keys_with_id_suffix = [key for key in primary_keys[file] if key.endswith('id')]
            label = f"{file}\n({table_types[file]})"
            dot.node(file, label=label, shape='box', style='filled', color='lightgray')

        # Add edges for primary key to foreign key relationships
        for key, tables in foreign_keys.items():
            for table in tables:
                for file in primary_keys:
                    if key in primary_keys[file]:
                        dot.edge(file, table, label=key)

        output_path = 'output/er_diagram'
        dot.render(output_path, view=False)
        # Specify paths for saving .dot and .png files
        dot_path = os.path.join(UPLOAD_FOLDER, 'er_diagram')
        png_path = os.path.join(UPLOAD_FOLDER, 'er_diagram')

        # Save the diagram as .dot file
        with open(dot_path, 'w') as f:
            f.write(dot.source)

        # Render the diagram as .png
        dot.render(png_path, format='png')

        return primary_keys, dot_path, png_path

    except Exception as e:
        # Log the exception for debugging
        print(f"Error generating ER diagram: {str(e)}")
        return None, str(e), None




# Route for index page
@app.route('/')
def index():
    return render_template('index.html')

# Route for uploading CSV files
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    try:
    
        files = request.files.getlist('files[]')

        if not files:
            return jsonify({'message': 'No selected files'}), 400

        for file in files:
            if file.filename == '':
                return jsonify({'message': 'No selected file'}), 400
            if file and file.filename.endswith('.csv'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

        return jsonify({'message': 'Files successfully uploaded'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to upload files: {str(e)}'}), 500

# Route for generating ER diagram
@app.route('/generate_er_diagram_route', methods=['GET'])
def generate_er_diagram_route():
    try:
        primary_keys, dot_path, png_path = generate_er_diagram()
        if dot_path :
            return jsonify({'primary_keys': primary_keys, 'dot_path': dot_path})
        else:
            return jsonify({'message': 'Failed to generate ER diagram'}), 500
    except Exception as e:
        return jsonify({'primary_keys': primary_keys, 'dot_path': dot_path})

# Route for downloading ER diagram .dot file
@app.route('/download_er_diagram_dot', methods=['GET'])
def download_er_diagram_dot():
    try:
        dot_path = os.path.join(app.config['UPLOAD_FOLDER'], 'er_diagram.dot')
        if os.path.exists(dot_path):
            return send_file(dot_path, as_attachment=True)
        else:
            return jsonify({'message': 'ER diagram .dot file not found'}), 404
    except Exception as e:
        return jsonify({'message': f'Failed to download ER diagram .dot file: {str(e)}'}), 500

# Route for serving ER diagram PNG file
@app.route('/serve_er_diagram_png', methods=['GET'])
def serve_er_diagram_png():
    try:
        png_path = os.path.join(app.config['UPLOAD_FOLDER'], 'er_diagram.png')
        if os.path.exists(png_path):
            return send_file(png_path, mimetype='image/png')
        else:
            return jsonify({'message': 'ER diagram PNG file not found'}), 404
    except Exception as e:
        return jsonify({'message': f'Failed to serve ER diagram PNG: {str(e)}'}), 500

@app.route('/start_chat', methods=['POST'])
def start_chat():
    try:
        chat = genai.GenerativeModel('gemini-1.5-flash').start_chat(history=[])
        return jsonify({'chat_id': chat.id}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to start chat: {str(e)}'}), 500

def to_markdown(text):
    text = text.replace('.', ' *')
    return Markdown(textwrap.indent(text, '--', predicate=lambda _: True))

@app.route('/convert_expression', methods=['POST'])
def convert_expression():
    data = request.json
    chat_id = data.get("chat_id", "")
    message = data.get("message", "")

    try:
        response = model.generate_content(f"Convert this tableau expression into dax expression. Give me the dax query as output not give the explanation at any point do not give explanation for expression{message}")
        print(response)
    
        if response.candidates:
            # Extracting and formatting the DAX expression
            dax_expression = response.candidates[0].content.parts[0].text.strip()
            formatted_dax = f"\n {dax_expression.replace(' ', ' ')}\n "
            

            return jsonify({'dax_expression': f"{formatted_dax}"}), 200
        else:
            return jsonify({'message': 'No valid DAX expression found in response'}), 500

    except Exception as e:
        return jsonify({'message': f'Failed to generate DAX expression: {str(e)}'}), 500

@app.route('/delete_files', methods=['POST'])
def delete_files():
    try:
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

        return jsonify({'message': 'Files successfully deleted'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to delete files: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
