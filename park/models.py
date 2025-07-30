from django.db import models


class Park(models.Model):
    """"Информация о парке"""
    park_id = models.CharField(
        max_length=50,
        verbose_name='id парка',
        unique=True
    )
    api_key = models.CharField(
        max_length=50,
        verbose_name='api ключ'
    )
    client_id = models.CharField(
        max_length=50,
        verbose_name='id клиента',
        blank=True,
        null=True,
        default=None
    )
    name = models.CharField(
        max_length=255,
        verbose_name='название',
        blank=True,
    )
    city = models.CharField(
        max_length=50,
        verbose_name='город',
        blank=True,
    )
    is_active = models.BooleanField(default=True, verbose_name='активен')

    class Meta:
        verbose_name = 'парк'
        verbose_name_plural = 'парки'
        ordering = ['city']

    def __str__(self):
        return f'{self.city} - {self.name}'

    def save(self, *args, **kwargs):
        # Получаем информацию о парке
        from park.utils import get_park_info
        park_info = get_park_info(self.park_id, self.api_key, self.client_id)
        if park_info:
            # Обновляем атрибуты объекта
            self.city = park_info.get('city')
            self.name = park_info.get('name')

        # Вызываем оригинальный метод save() для сохранения объекта в базу данных
        super().save(*args, **kwargs)


class Car(models.Model):
    """Автомобиль"""
    park = models.ForeignKey(Park, on_delete=models.CASCADE, verbose_name='парк')
    car_id = models.CharField(max_length=32, verbose_name='автомобиль', unique=True)
    brand = models.CharField(max_length=255, verbose_name='бренд')
    model = models.CharField(max_length=255, verbose_name='модель')
    year = models.PositiveSmallIntegerField(verbose_name='год')
    vin = models.CharField(max_length=255, verbose_name='vin', blank=True)
    color = models.CharField(max_length=255, verbose_name='цвет')
    number = models.CharField(max_length=255, verbose_name='государственный номер')
    callsign = models.CharField(max_length=255, verbose_name='позывной')
    status = models.CharField(max_length=255, verbose_name='статус')
    amenities = models.CharField(max_length=255, verbose_name='удобства', blank=True)
    category = models.CharField(max_length=255, verbose_name='категория ТС', blank=True)
    registration_cert = models.CharField(mmax_length=255, verbose_name='свидетельство о регистрации')
    is_park_property = models.BooleanField(verbose_name='собственность парка', default=False)

    class Meta:
        verbose_name = 'автомобиль'
        verbose_name_plural = 'автомобили'
        ordering = ['pk']

    def __str__(self):
        return f'{self.car_id} {self.brand} {self.model}'


class DriverWorkRule(models.Model):
    """Условия работы водителя"""
    park = models.ForeignKey(Park, on_delete=models.CASCADE, verbose_name='парк')
    work_rule_id = models.CharField(max_length=32, verbose_name='идентификатор условия работы')
    is_enabled = models.BooleanField(verbose_name='доступно')
    name = models.CharField(max_length=255, verbose_name='название')

    class Meta:
        unique_together = ('park', 'work_rule_id')
        verbose_name = 'условие работы'
        verbose_name_plural = 'условия работы'
        ordering = ['name']

    def __str__(self):
        return self.name


class Account(models.Model):
    """Счет водителя"""
    account_id = models.CharField(max_length=32, verbose_name='id аккаунта', unique=True, db_index=True)
    balance = models.CharField(max_length=255, verbose_name='баланс', default=0)
    balance_limit = models.CharField(max_length=255, verbose_name='ограничение баланса', default=0,)
    currency = models.CharField(max_length=255, verbose_name='валюта',)
    account_type = models.CharField(max_length=255, verbose_name='тип счета',)

    class Meta:
        verbose_name = 'счет водителя'
        verbose_name_plural = 'счет водителя'
        ordering = ['name']

    def __str__(self):
        return self.account_id


class Driver(models.Model):
    """Водитель"""
    park = models.ForeignKey(
        Park,
        on_delete=models.CASCADE,
        verbose_name='парк',
        related_name='driver_park'
    )
    driver_profile_id = models.CharField(max_length=32, verbose_name='id водителя', unique=True, db_index=True)
    last_name = models.CharField(max_length=255, verbose_name='фамилия')
    first_name = models.CharField(max_length=255, verbose_name='имя')
    middle_name = models.CharField(max_length=255, verbose_name='отчество', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Номер телефона', blank=True)
    driver_license_number = models.CharField(max_length=255, verbose_name='номер ВУ', blank=True)
    driver_license_country = models.CharField(max_length=255, verbose_name='страна ВУ', blank=True,)
    driver_license_issue_date = models.CharField(max_length=255, verbose_name='дата выдачи ВУ', blank=True)
    driver_license_expiration_date = models.CharField(ь_length=255, verbose_name='дата окончания ВУ', blank=True)
    work_status = models.CharField(max_length=255, verbose_name='статус работы водителя', blank=True,)
    work_rule_id = models.ForeignKey(
        DriverWorkRule,
        on_delete=models.PROTECT,
        verbose_name='условия работы',
        blank=True,
        null=True,
        default=None
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        verbose_name='счет',
        blank=True,
        null=True,
        default=None
    )
    created_date = models.CharField(max_length=255, verbose_name='дата создания', blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['driver_id'])
        ]
        unique_together = ('park', 'driver_id')
        verbose_name = 'водитель'
        verbose_name_plural = 'водители'
        ordering = ['last_name']

    def __str__(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'


class Order(models.Model):
    """Заказ"""
    park = models.ForeignKey(
        Park,
        on_delete=models.CASCADE,
        verbose_name='парк',
        related_name='order_park'
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        verbose_name='водитель',
        related_name='order_driver',
        db_index=True
    )
    order_id = models.CharField(max_length=255, verbose_name='id заказа', unique=True)
    created_at = models.DateTimeField(verbose_name='создан')
    status = models.CharField(ь_length=255, verbose_name='статус заказа', blank=True, default='')
    payment_method = models.CharField(max_length=255, verbose_name='способ оплаты', blank=True, default='')
    price = models.DecimalField(decimal_places=4, max_digits=15, verbose_name='стоимость')
    car = models.ForeignKey(
        Car,
        on_delete=models.PROTECT,
        verbose_name='автомобиль',
        blank=True,
        null=True,
        default=None
    )
    cancellation_description = models.CharField(max_length=255, verbose_name='описание отмены', blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['order_id'])
        ]
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        ordering = ['-ended_at']

    def __str__(self):
        return f'{self.driver.last_name} {self.driver.first_name} {self.driver.middle_name}'


class TransactionCategory(models.Model):
    """Категории транзакций"""
    category_id = models.CharField(max_length=255, verbose_name='id категории', unique=True, db_index=True)
    name = models.CharField(max_length=255, verbose_name='название категории')
    group_id = models.CharField(max_length=255, verbose_name='id группы', blank=True, default='')
    group_name = models.CharField(max_length=255, verbose_name='название группы', blank=True, default='')

    class Meta:
        verbose_name = 'категория транзакции'
        verbose_name_plural = 'категории транзакций'
        ordering = ['-event_at']

    def __str__(self):
        return self.name


class Transaction(models.Model):
    """Транзакции"""
    park = models.ForeignKey(
        Park,
        on_delete=models.CASCADE,
        verbose_name='парк',
        related_name='transaction_park'
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        verbose_name='водитель',
        related_name='transaction_driver',
        db_index=True
    )

    transaction_id = models.CharField(max_length=255, verbose_name='id заказа', unique=True)
    event_at = models.DateTimeField(verbose_name='завершен')
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.PROTECT,
        verbose_name='категория',
        blank=True,
        null=True,
        default=None
    )
    name = models.CharField(max_length=255, verbose_name='название категории', blank=True, default='')
    group_id = models.CharField(max_length=255, verbose_name='id группы', blank=True, default='')
    group_name = models.CharField(max_length=255, verbose_name='название группы', blank=True, default='')
    amount = models.DecimalField(decimal_places=4, max_digits=15, verbose_name='стоимость')
    description = models.CharField(max_length=255, verbose_name='описание')

    class Meta:
        indexes = [
            models.Index(fields=['transaction_id'])
        ]
        verbose_name = 'транзакция'
        verbose_name_plural = 'транзакции'
        ordering = ['-event_at']

    def __str__(self):
        return f'{self.driver.last_name} {self.driver.first_name} {self.driver.middle_name}'


class RegularChargesError(models.Model):
    """Ошибки периодических списаний"""
    park = models.ForeignKey(
        Park,
        on_delete=models.PROTECT,
        verbose_name='парк',
        related_name='regular_charges_error_park'
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        verbose_name='водитель',
        related_name='regular_charges_error_driver',
        db_index=True
    )
    daily_price = models.DecimalField(verbose_name='размер списания', max_digits=9, decimal_places=4, default=0)
    order = models.BooleanField(verbose_name='заказ', default=True)
    transaction = models.BooleanField(verbose_name='транзакция', default=True)
    date = models.DateField(verbose_name='дата')

    class Meta:
        unique_together = [['park', 'driver', 'date']]
        indexes = [
            models.Index(fields=['driver'])
        ]
        verbose_name = 'ошибки периодических списаний'
        verbose_name_plural = 'ошибки периодических списаний'
        ordering = ['-date']

    def __str__(self):
        return f'{self.driver.last_name} {self.driver.first_name} {self.driver.middle_name}'


class CalculateDriverStatus(models.Model):
    """Дата сет статусов водителей по дням"""
    park = models.ForeignKey(
        Park,
        on_delete=models.CASCADE,
        verbose_name='парк',
        related_name='calculate_driver_status_park'
    )
    count_active_individual_entrepreneur = models.PositiveIntegerField(verbose_name='активные ИП', default=0)
    count_active_selfemployed = models.PositiveIntegerField(verbose_name='активные СМЗ', default=0)
    count_active_park_employee = models.PositiveIntegerField(verbose_name='активные водители', default=0)
    count_outflow_individual_entrepreneur = models.PositiveIntegerField(verbose_name='отток ИП', default=0)
    count_outflow_selfemployed = models.PositiveIntegerField(verbose_name='отток СМЗ', default=0)
    count_outflow_park_employee = models.PositiveIntegerField(verbose_name='отток водители', default=0)
    count_archive_individual_entrepreneur = models.PositiveIntegerField(verbose_name='архив ИП', default=0)
    count_archive_selfemployed = models.PositiveIntegerField(verbose_name='архив СМЗ', default=0)
    count_archive_park_employee = models.PositiveIntegerField(verbose_name='архив водители', default=0)
    date = models.DateField(verbose_name='дата')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата добавления')

    def __str__(self):
        return f'{self.park.name} ({self.park.city})'

    class Meta:
        unique_together = [('park', 'date')]
        verbose_name = 'количество статусов по дням'
        verbose_name_plural = 'количество статусов по дням'
        ordering = ['-date']


class CountActiveDriver(models.Model):
    """Количество активных водителей по дням"""
    park = models.ForeignKey(
        Park,
        on_delete=models.CASCADE,
        verbose_name='парк',
        related_name='count_active_driver_park'
    )
    count_active_individual_entrepreneur = models.PositiveIntegerField(verbose_name='активные ИП', default=0)
    count_active_park_employee = models.PositiveIntegerField(verbose_name='активные водители', default=0)
    count_active_selfemployed = models.PositiveIntegerField(verbose_name='активные СМЗ', default=0)
    count_total = models.PositiveIntegerField(verbose_name='общие число активных водителей', default=0)
    period = models.PositiveSmallIntegerField(verbose_name='период', default=1)
    created_at = models.DateField(auto_now_add=True, verbose_name='дата добавления')

    def __str__(self):
        return f'{self.park.name}'

    class Meta:
        indexes = [
            models.Index(fields=['park']),  # Индексация по полю park
            models.Index(fields=['created_at']),  # Индексация по полю created_at
            models.Index(fields=['period']),  # Индексация по полю period
        ]

        unique_together = [('park', 'created_at', 'period')]
        verbose_name = 'количество активных водителей по дням'
        verbose_name_plural = 'количество активных водителей по дням'
        ordering = ['-created_at']

