1. Start the Databases
Run this command to initialize PostgreSQL, Neo4j, and Weaviate. Note: Wait 10-20 seconds after this command for the databases to fully initialize.
./scripts/run-db.sh

2. Start the Applications
Once the databases are ready, run this to start the Backend, Frontend, and Redis:
./scripts/run-apps.sh

Stop Everything
To stop all services and free up ports:
./scripts-all.sh

📂 Architecture & Services
The system is split into two Docker Compose configurations to ensure the data layer is healthy before the application layer attempts to connect.

Data Layer (start-db.sh)
These services handle data persistence.

Application Layer (start-apps.sh)
These services handle the logic and user interface.

⚙️ Configuration (.env)
The project relies on environment variables. Ensure you have a .env file in your project root (or specific app folders) defining the following:
sao_chatbot_backend
sao_chatbot_frontend