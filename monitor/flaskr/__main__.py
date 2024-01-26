from flaskr import create_app
import os

def main():
    FLASK_PORT = os.getenv('FLASK_PORT')

    app = create_app()
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=True)

if __name__ == '__main__':
    main()