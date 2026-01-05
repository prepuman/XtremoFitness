import sqlalchemy as db

# Creamos el engine UNA SOLA VEZ para que toda la aplicación lo comparta.
# echo=False es mejor para el uso normal, para no llenar la consola de texto.
engine = db.create_engine('sqlite:///bd/xtremo.sqlite', echo=False, future=True)