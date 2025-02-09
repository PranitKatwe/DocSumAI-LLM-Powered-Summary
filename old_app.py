from flask import Flask, request, jsonify
from google.cloud import storage
import psycopg2
from google.cloud import pubsub_v1
import os
import logging
from PyPDF2 import PdfReader
from docx import Document
from transformers import AutoTokenizer, BartForConditionalGeneration, PegasusForConditionalGeneration, PegasusTokenizer

# Initialize Flask app
app = Flask(__name__)

# Configure GCP services
BUCKET_NAME = "doc-upload-bucket"
PROJECT_ID = "document-summarizer-441617"
TOPIC_NAME = "doc-process-topic"

# Initialize GCP clients
storage_client = storage.Client()
publisher = pubsub_v1.PublisherClient()

# Database connection
DB_CONFIG = {
    "host": "35.222.168.43",  # Replace with your Cloud SQL public IP
    "database": "summarization_db",
    "user": "postgres",
    "password": "postgres"
}

logging.basicConfig(level=logging.DEBUG)

# Initialize Hugging Face models and tokenizers
bart_model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
bart_tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")

pegasus_model = PegasusForConditionalGeneration.from_pretrained("google/pegasus-large")
pegasus_tokenizer = PegasusTokenizer.from_pretrained("google/pegasus-large")

MAX_TOKENS = 1024  # Maximum token limit for the summarizer model


def extract_text(file_path):
    """Extract text from PDF, Word, or TXT files."""
    ext = os.path.splitext(file_path)[1].lower()
    extracted_text = ""

    if ext == ".pdf":
        with open(file_path, "rb") as pdf_file:
            reader = PdfReader(pdf_file)
            extracted_text = " ".join([page.extract_text() for page in reader.pages])
    elif ext == ".docx":
        doc = Document(file_path)
        extracted_text = "\n".join([p.text for p in doc.paragraphs])
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as txt_file:
            extracted_text = txt_file.read()
    else:
        raise ValueError("Unsupported file type")

    if not extracted_text.strip():
        raise ValueError("No text extracted from the file.")

    logging.info(f"Extracted text length: {len(extracted_text)}")
    return extracted_text


def tokenize_and_chunk(text, tokenizer, max_tokens=MAX_TOKENS):
    """Tokenize and chunk the text."""
    tokens = tokenizer(text, return_tensors="pt", truncation=False)["input_ids"][0]
    logging.info(f"Total tokens in text: {len(tokens)}")

    if len(tokens) <= max_tokens:
        return [tokenizer.decode(tokens, skip_special_tokens=True)]
    
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk = tokens[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk, skip_special_tokens=True)
        if len(chunk_text.strip()) > 0:
            chunks.append(chunk_text)
    
    logging.info(f"Total chunks created: {len(chunks)}")
    return chunks


def summarize_text(text, summary_type, preferred_model="bart"):
    """Generate summary using Bart or Pegasus."""
    logging.info(f"Input text length: {len(text)} characters")
    
    # Define summary length limits based on summary_type
    if summary_type == "short":
        max_length, min_length = 150, 50
    elif summary_type == "medium":
        max_length, min_length = 250, 100
    elif summary_type == "long":
        max_length, min_length = 500, 250
    else:
        raise ValueError("Invalid summary type")

    model, tokenizer = (
        (bart_model, bart_tokenizer) if preferred_model == "bart" else
        (pegasus_model, pegasus_tokenizer)
    )

    # Tokenize input text
    inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)

    logging.info(f"Tokenized input length: {inputs['input_ids'].shape[1]} tokens")

    try:
        # Generate summary with dynamic max_length and min_length based on summary_type
        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=max_length,
            min_length=min_length,
            length_penalty=2.0,
            num_beams=4
        )
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary
    except Exception as e:
        logging.error(f"Error summarizing text: {str(e)}")
        return f"Error summarizing text: {str(e)}"


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/upload', methods=['POST'])
def upload_document():
    try:
        # Get the file and summary type from the request
        file = request.files['file']
        summary_type = request.form.get('summary_type', 'short')  # Default to short if not specified
        model_choice = request.form.get('model', 'bart').lower()  # Get model choice ('bart' or 'pegasus')
        
        # Ensure valid summary type and model
        if summary_type not in ['short', 'medium', 'long']:
            return jsonify({"error": "Invalid summary type. Choose 'short', 'medium', or 'long'."}), 400
        if model_choice not in ['bart', 'pegasus']:
            return jsonify({"error": "Invalid model. Choose 'bart' or 'pegasus'."}), 400
        
        file_name = file.filename
        temp_file_path = f"/tmp/{file_name}"

        # Save the file temporarily
        file.save(temp_file_path)
        logging.info(f"File saved temporarily at {temp_file_path}")

        # Extract text and summarize
        extracted_text = extract_text(temp_file_path)
        if len(extracted_text.strip()) < 50:
            return jsonify({"error": "Extracted text is too short to generate a meaningful summary."}), 400

        summary = summarize_text(extracted_text, summary_type, model_choice)
        logging.info(f"Generated {summary_type} summary: {summary}")

        # Upload the file to Cloud Storage
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_name)
        blob.upload_from_filename(temp_file_path)
        logging.info(f"File {file_name} uploaded to {BUCKET_NAME}")

        # Save metadata to Cloud SQL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (file_name, summary) VALUES (%s, %s) RETURNING id",
            (file_name, summary)
        )
        document_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        # Publish a message to Pub/Sub
        message = {"document_id": document_id, "file_name": file_name}
        publisher.publish(f"projects/{PROJECT_ID}/topics/{TOPIC_NAME}", str(message).encode('utf-8'))

        # Clean up temporary file
        os.remove(temp_file_path)

        # Return the response with the document ID and summary
        return jsonify({
            "message": "Document uploaded successfully!",
            "document_id": document_id,
            "summary": summary,
            "summary_type": summary_type
        }), 200

    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
