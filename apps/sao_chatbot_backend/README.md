To run this server locally

1.  create python venv using 
python -m venv venv

2. activate the venv
source venv/bin/activate 
for window
.\venv\Scripts\activate

3. install necessary library using
pip install -r requirements.txt

4. to start server locally run
uvicorn main:app --reload

your server should be starting at localhost:8000
#note this server require database from weaviate and postgres to functional