# **Document Summarizer Service**

A cloud-based application that leverages state-of-the-art NLP models to generate concise summaries for documents uploaded in various formats (PDF, DOCX, TXT). This project is built with Python, Flask, Docker, and Google Cloud services, ensuring scalability and performance.


# **Team Members**

Pranit Katwe

Sawani Hejib

---

## **Features**
- Upload documents in PDF, Word (DOCX), or TXT formats.
- Generate summaries in three formats: **short**, **medium**, and **long**.
- Choose between two powerful NLP models: **BART** and **Pegasus**.
- Asynchronous processing using Google Cloud Pub/Sub.
- Secure storage with Google Cloud Storage and metadata management using Cloud SQL.
- Scalable deployment using Docker and Kubernetes.

---

## **Setup**

### **2. Prerequisites**
1. Python 3.10 or higher.
2. Google Cloud SDK installed and authenticated.
3. Docker installed for containerized deployment.
4. Google Cloud project with:
   - A Pub/Sub topic and subscription.
   - A Cloud Storage bucket.
   - A Cloud SQL instance.
5. Hugging Face Transformers installed for BART and Pegasus models.

---

### **3. Local Environment Setup**
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/pranitkatwe/document-summarizer.git
   cd document-summarizer
2. Set Up Virtual Environment:
   ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
3. Install Dependencies:
   ```bash
    pip install -r requirements.txt
4. Authenticate Google Cloud
   ```bash
   gcloud auth login
    gcloud config set project [PROJECT_ID]
    gcloud auth application-default login
    export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account.json"
 5. Run the Application:\
    ```bash
    python app.py
  Access the service at http://127.0.0.1:5000/. or [localhost:5000](http://localhost:5000/.)
  
### **4. Docker Deployment**
1. Build Docker image
2. Run the container
3. Access the application at http://localhost:5000/. or http://127.0.0.1:5000/.


### **5.Application Components**
- Frontend
1. HTML, CSS, and JavaScript interface for uploading documents, selecting summary types, and viewing results.
- Backend
1. Flask: Provides API endpoints for upload and summarization.
2. Hugging Face Models: Implements BART and Pegasus for summarization.
- Google Cloud Integration
1. Cloud Storage: Stores uploaded documents securely.
2. Pub/Sub: Manages asynchronous processing of document tasks.
3. Cloud SQL: Stores metadata and generated summaries.


### **API Endpoints**
Upload Document
URL: /upload
Method: `POST`
Parameters:
`file`: The document file (PDF, DOCX, or TXT).
`summary_type`: `short`, `medium`, or `long`.
`model`: `bart` or `pegasus`.
