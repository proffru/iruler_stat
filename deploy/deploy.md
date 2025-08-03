# SSH
## На локальном коипьютере

    cd C:\Users\yurii\.ssh

    ssh-keygen -t rsa -b 4096

задаем название файла, пример ruvds

### заходим на сервер
Создайте папку .ssh в домашней директории пользователя:

    mkdir -p .ssh
    cd .ssh

Добавьте в файл authorized_keys публичный ключ нового пользователя

    nano authorized_keys

Добавляем ключ, сохраняем файл

## На удаленном сервере

    ssh -p 22 root@217.114.12.183 -i ~/.ssh/kozlove
    
Для быстрого запуска виртуального окружения
    
    cd /home/report/
    source /home/report/venv/bin/activate

    supervisorctl stop all
    supervisorctl reread
    supervisorctl update
    supervisorctl start all
    service nginx reload
    service nginx restart

Отключаем вход по паролю

    cd ../etc/ssh/
    nano sshd_config

    PasswordAuthentication no
    systemctl restart ssh
	
	cd /etc/ssh/sshd_config.d/
    nano 50-cloud-init.conf
    systemctl reload ssh

# Настройка сервера
    apt-get update
    apt-get upgrade

    sudo apt install python3-pip python3-dev python3-venv libpq-dev postgresql postgresql-contrib nginx supervisor daphne
    sudo apt-get install build-essential libssl-dev libffi-dev python3-certbot-nginx certbot gcc python3-wheel

## redis
    sudo apt-get install redis-server
    sudo systemctl enable redis-server.service


# Настройки бэкэнд
    mkdir /home/report
    cd /home/report

## Создаем и настраиваем виртуальное окружение
    python3 -m venv venv
    source venv/bin/activate
    pip3 install wheel

## Установка пакетов

    python manage.py migrate
    python manage.py collectstatic

# Настройка nginx
    cd /etc/nginx/sites-available

Устанавливаем наш конфиг

    service nginx restart

# Supervisor
    cd /etc/supervisor/conf.d
Устанавливаем наш конфиг

    supervisorctl stop all
    supervisorctl reread
    supervisorctl update
    supervisorctl start all
    service nginx reload
    service nginx restart


# SSL
Проверить nginx nginx -t

    sudo certbot certonly --nginx -d agent-report.ru -d www.agent-report.ru


# Безопасность 

    sudo apt install fail2ban

## Создайте 2 файла (лежит в директории)

nginx-bad-requests.conf 

nginx-bad-bots.conf 

и положить в директорию
    
    /etc/fail2ban/filter.d/

файл jail.local

положить в директорию 

    /etc/fail2ban/


# Импорт/Экспорт

## Экспорт

    python manage.py dumpdatautf8 mobile --indent 2 --output data.json

## Импорт
    
    python manage.py loaddata data.json
    python manage.py loaddata data.json.gz --exclude contenttypes --exclude auth.permission

# Миграции

## Объединить в одну

    python manage.py squashmigrations <app> <last_mogration>
    python manage.py squashmigrations main 0018_delete_notification

# Резервная копия БД

## Создание копии
Выполняем на старом сервере

    pg_dump -U <имя_пользователя> -h <адрес_хоста> <имя_базы_данных> > <имя_файла_резервной_копии>.sql
    pg_dump -U docsdbuser -h 194.87.76.84 -d agentreport -Fc > /home/report/db.sql

Скопируем файл резервной копии на новый VPS

## Восстановление резервную копию базы данных
Выполняем на новом сервере

    psql -U <имя_пользователя> -h <адрес_хоста> -d <имя_новой_базы_данных> -f <имя_файла_резервной_копии>.sql
    psql -U cloud_user -h tuenakopob.beget.app -d agent_report -f /home/report/db.sql

    pg_restore \
    -U cloud_user \
    -h 10.16.0.2 \
    -d agent_report \
    --no-owner \
    --no-acl \
    --no-comments \
    /home/report/dump.pg

