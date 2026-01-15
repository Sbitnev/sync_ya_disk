# Alembic Миграции

Этот проект использует [Alembic](https://alembic.sqlalchemy.org/) для управления миграциями базы данных.

## Основные команды

### Проверка текущей версии БД
```bash
alembic current
```

### Просмотр истории миграций
```bash
alembic history
```

### Создание новой миграции
```bash
# Создать пустую миграцию
alembic revision -m "описание_изменений"

# Пример: добавление новой колонки
alembic revision -m "add_user_email_column"
```

### Применение миграций
```bash
# Применить все миграции до последней версии
alembic upgrade head

# Применить одну миграцию вперед
alembic upgrade +1

# Применить до конкретной версии
alembic upgrade <revision_id>
```

### Откат миграций
```bash
# Откатить одну миграцию назад
alembic downgrade -1

# Откатить до конкретной версии
alembic downgrade <revision_id>

# Откатить все миграции
alembic downgrade base
```

## Структура файла миграции

Каждая миграция содержит две функции:

```python
def upgrade() -> None:
    """Применение изменений"""
    # Добавление колонки
    op.add_column('files', sa.Column('new_column', sa.Text(), nullable=True))

    # Создание индекса
    op.create_index('idx_new_column', 'files', ['new_column'])

def downgrade() -> None:
    """Откат изменений"""
    # Удаление индекса
    op.drop_index('idx_new_column', table_name='files')

    # Удаление колонки
    op.drop_column('files', 'new_column')
```

## Автоматическое применение миграций

Миграции применяются автоматически при инициализации `MetadataDatabase`:

```python
from src.database import MetadataDatabase
from src import config

# Миграции применятся автоматически
db = MetadataDatabase(config.METADATA_DB_PATH)

# Отключить автоматическое применение
db = MetadataDatabase(config.METADATA_DB_PATH, auto_migrate=False)
```

## Примеры изменений схемы

### Добавление новой колонки
```python
def upgrade() -> None:
    op.add_column('files', sa.Column('file_hash', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('files', 'file_hash')
```

### Создание новой таблицы
```python
def upgrade() -> None:
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('sync_logs')
```

### Создание индекса
```python
def upgrade() -> None:
    op.create_index('idx_files_size', 'files', ['size'])

def downgrade() -> None:
    op.drop_index('idx_files_size', table_name='files')
```

### Изменение типа колонки (SQLite ограничение)
```python
# SQLite не поддерживает ALTER COLUMN напрямую
# Нужно создать новую таблицу и перенести данные

def upgrade() -> None:
    # 1. Создать временную таблицу с новой схемой
    op.create_table(
        'files_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),  # Изменили тип
        # ... остальные колонки
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Скопировать данные
    op.execute('INSERT INTO files_new SELECT * FROM files')

    # 3. Удалить старую таблицу
    op.drop_table('files')

    # 4. Переименовать новую таблицу
    op.rename_table('files_new', 'files')

def downgrade() -> None:
    # Обратный процесс
    pass
```

## Best Practices

1. **Всегда заполняйте функцию `downgrade()`** - это позволяет откатывать изменения
2. **Тестируйте миграции** - проверяйте upgrade и downgrade на копии БД
3. **Используйте описательные имена** - `add_user_email_column` лучше чем `migration_001`
4. **Одна логическая единица изменений** - не смешивайте разные изменения в одной миграции
5. **Делайте резервные копии БД** перед применением миграций на продакшене

## Проблемы и решения

### Миграция не применяется автоматически
- Проверьте, что `auto_migrate=True` (по умолчанию)
- Проверьте логи на наличие ошибок
- Примените миграции вручную: `alembic upgrade head`

### "Table already exists" при создании новой БД
- Удалите файл БД и создайте заново
- Или используйте `alembic stamp head` для пометки текущей версии

### Конфликт версий миграций
- Используйте `alembic heads` для проверки веток
- Слейте ветки с помощью `alembic merge`

## Полезные ссылки

- [Документация Alembic](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [SQLite ALTER TABLE limitations](https://www.sqlite.org/lang_altertable.html)
