# Run database migrations
mig:
	@echo "Running database migrations..."
	@python3 manage.py makemigrations
	@python3 manage.py migrate

# Create superuser for the admin panel
adm:
	@echo "Creating superuser for the admin panel..."
	@python3 ./manage.py createsuperuser
	@echo "Superuser created."

# Create application
app:
	@echo "Creating app... ${name}"
	@python3 ./manage.py startapp ${name}

messages:
	@python3 manage.py makemessages -l en -i venv --verbosity=0
	@python3 manage.py makemessages -l uz -i venv --verbosity=0

com_mes:
	@python3 manage.py compilemessages --verbosity=0

gen:
	@echo "Generating fake data"
	@python3 manage.py generate_fake_data
	@echo "Fake data generated"

first_mes: messages com_mes
mig_gen: mig gen
