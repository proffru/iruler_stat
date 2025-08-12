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
    status = models.CharField(max_length=255, verbose_name='статус', blank=True, default='')
    brand = models.CharField(max_length=255, verbose_name='бренд')
    model = models.CharField(max_length=255, verbose_name='модель')
    year = models.PositiveSmallIntegerField(verbose_name='год')
    vin = models.CharField(max_length=255, verbose_name='vin', blank=True)
    color = models.CharField(max_length=255, verbose_name='цвет')
    number = models.CharField(max_length=255, verbose_name='государственный номер')
    callsign = models.CharField(max_length=255, verbose_name='позывной')
    status = models.CharField(max_length=255, verbose_name='статус')
    amenities = models.CharField(max_length=1500, verbose_name='удобства', blank=True)
    category = models.CharField(max_length=1500, verbose_name='категория ТС', blank=True)
    registration_cert = models.CharField(max_length=255, verbose_name='свидетельство о регистрации')

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
        ordering = ['account_id']

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
    driver_id = models.CharField(max_length=32, verbose_name='id водителя', unique=True, db_index=True)
    last_name = models.CharField(max_length=255, verbose_name='фамилия')
    first_name = models.CharField(max_length=255, verbose_name='имя')
    middle_name = models.CharField(max_length=255, verbose_name='отчество', blank=True)
    driver_license_number = models.CharField(max_length=255, verbose_name='номер ВУ', blank=True)
    driver_license_country = models.CharField(max_length=255, verbose_name='страна ВУ', blank=True,)
    driver_license_issue_date = models.CharField(
        max_length=255,
        verbose_name='дата выдачи ВУ',
        blank=True,
        null=True,
        default=None
    )
    driver_license_expiration_date = models.CharField(
        max_length=255,
        verbose_name='дата окончания ВУ',
        blank=True,
        null=True,
        default=None
    )
    work_status = models.CharField(max_length=255, verbose_name='статус работы водителя', blank=True,)
    work_rule = models.ForeignKey(
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
    order_id = models.CharField(max_length=255, verbose_name='id заказа', unique=True, db_index=True)
    short_id = models.CharField(max_length=255, verbose_name='короткий id заказа')
    created_at = models.DateTimeField(verbose_name='создан')
    status = models.CharField(max_length=255, verbose_name='статус заказа', blank=True, default='')
    category = models.CharField(max_length=255, verbose_name='категория', blank=True, default='')
    payment_method = models.CharField(max_length=255, verbose_name='способ оплаты', blank=True, default='')
    price = models.DecimalField(decimal_places=4, max_digits=15, verbose_name='стоимость')
    address_from = models.CharField(max_length=500, verbose_name='адрес откуда', blank=True, default='')
    address_from_lat = models.CharField(max_length=50, verbose_name='адрес откуда широта', blank=True, default='')
    address_from_lon = models.CharField(max_length=50, verbose_name='адрес откуда долгота', blank=True, default='')
    address_to = models.CharField(max_length=500, verbose_name='адрес куда', blank=True, default='')
    address_to_lat = models.CharField(max_length=50, verbose_name='адрес куда широта', blank=True, default='')
    address_to_lon = models.CharField(max_length=50, verbose_name='адрес куда долгота', blank=True, default='')
    mileage = models.CharField(max_length=255, verbose_name='пробег', blank=True, default=0)
    car = models.ForeignKey(
        Car,
        on_delete=models.PROTECT,
        verbose_name='автомобиль',
        blank=True,
        null=True,
        default=None
    )
    cancellation_description = models.CharField(max_length=255, verbose_name='описание отмены', blank=True, default='')
    load_transaction_complete = models.BooleanField(verbose_name='загрузка транзакций завершена', default=False)

    class Meta:
        indexes = [
            models.Index(fields=['order_id'])
        ]
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.driver.last_name} {self.driver.first_name} {self.driver.middle_name}'


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
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='заказ',
        related_name='transaction_order',
        db_index=True
    )

    transaction_id = models.CharField(max_length=255, verbose_name='id заказа', unique=True)
    event_at = models.DateTimeField(verbose_name='завершен')
    category_id = models.CharField(max_length=255, verbose_name='id категории', blank=True, default='')
    category_name = models.CharField(max_length=255, verbose_name='название категории', blank=True, default='')
    group_id = models.CharField(max_length=255, verbose_name='группа', blank=True, default='')
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


class OrdersLoadState(models.Model):
    """Статус загрузки заказов"""
    last_loaded_datetime = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OrdersLoadState(last_loaded_datetime={self.last_loaded_datetime})"

    class Meta:
        verbose_name = 'статус загрузки заказов'
        verbose_name_plural = 'статусы загрузки заказов'
        ordering = ['-updated_at']