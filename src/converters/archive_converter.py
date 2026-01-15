"""
Конвертер архивных файлов (.zip, .7z, .rar, .tar, .gz) в Markdown
"""
import tempfile
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Optional
from loguru import logger

from .base import FileConverter


class ArchiveConverter(FileConverter):
    """
    Конвертер архивов в Markdown

    Особенности:
    - Рекурсивная распаковка вложенных архивов
    - Использование существующих конвертеров для файлов
    - Защита от циклических архивов
    - Создание индексного файла + отдельные MD для каждого файла
    """

    def __init__(
        self,
        converters_registry: List[FileConverter] = None,
        max_depth: int = 10
    ):
        """
        :param converters_registry: Список других конвертеров для обработки файлов из архива
        :param max_depth: Максимальная глубина рекурсии
        """
        super().__init__(['.zip', '.7z', '.rar', '.tar', '.gz', '.tgz', '.tar.gz'])
        self.converters_registry = converters_registry or []
        self.max_depth = max_depth

        # Проверка библиотек
        self.has_zipfile = True  # Встроенная
        self.has_tarfile = True  # Встроенная
        self.has_py7zr = self._check_py7zr()
        self.has_rarfile = self._check_rarfile()
        self.has_patool = self._check_patool()

        if not (self.has_zipfile or self.has_tarfile):
            logger.error("Критическая ошибка: встроенные модули недоступны")

    # === Проверка зависимостей ===

    def _check_py7zr(self) -> bool:
        """Проверяет наличие py7zr для .7z архивов"""
        try:
            import py7zr
            return True
        except ImportError:
            return False

    def _check_rarfile(self) -> bool:
        """Проверяет наличие rarfile для .rar архивов"""
        try:
            import rarfile
            return True
        except ImportError:
            return False

    def _check_patool(self) -> bool:
        """Проверяет наличие patool (универсальный fallback)"""
        try:
            import patoolib
            return True
        except ImportError:
            return False

    # === Главный метод конвертации ===

    def convert(self, input_path: Path, output_path: Path) -> bool:
        """
        Конвертирует архив в Markdown

        :param input_path: Путь к архиву
        :param output_path: Путь к индексному .md файлу
        :return: True если успешно
        """
        return self._convert_with_depth(input_path, output_path, depth=0, archive_hashes=set())

    def _convert_with_depth(
        self,
        input_path: Path,
        output_path: Path,
        depth: int,
        archive_hashes: Set[str]
    ) -> bool:
        """Внутренний метод с отслеживанием глубины"""

        # Проверка глубины
        if depth > self.max_depth:
            logger.warning(f"Достигнута максимальная глубина ({self.max_depth}): {input_path.name}")
            return False

        # Проверка на циклы
        file_hash = self._calculate_file_hash(input_path)
        if file_hash in archive_hashes:
            logger.warning(f"Обнаружен циклический архив: {input_path.name}")
            return False

        archive_hashes.add(file_hash)

        logger.info(f"Обработка архива (глубина {depth}): {input_path.name}")

        # Создаем временную директорию
        temp_dir = Path(tempfile.mkdtemp(prefix="archive_extract_"))

        try:
            # Шаг 1: Распаковка
            extract_result = self._extract_archive(input_path, temp_dir)

            if not extract_result['success']:
                logger.error(f"Ошибка распаковки: {extract_result.get('error', 'Unknown')}")
                self._create_error_index(output_path, input_path, extract_result.get('error', 'Unknown'))
                return False

            extracted_files = extract_result['files']
            logger.debug(f"Извлечено файлов: {len(extracted_files)}")

            # Шаг 2: Создаем директорию для результатов
            output_dir = output_path.parent / f"{output_path.stem}_extracted"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Шаг 3: Обработка содержимого
            processing_result = self._process_extracted_files(
                extracted_files,
                temp_dir,
                output_dir,
                depth,
                archive_hashes
            )

            # Шаг 4: Создание индексного файла
            self._create_index_file(
                input_path,
                output_path,
                temp_dir,
                extracted_files,
                processing_result,
                depth
            )

            logger.success(f"Архив успешно обработан: {input_path.name}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при обработке архива {input_path.name}: {e}")
            self._create_error_index(output_path, input_path, str(e))
            return False

        finally:
            # Очистка временных файлов
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Не удалось удалить временную директорию: {e}")

    # === Методы распаковки ===

    def _extract_archive(self, archive_path: Path, extract_dir: Path) -> Dict:
        """Универсальный метод распаковки"""

        extension = archive_path.suffix.lower()

        # Определяем метод распаковки
        if extension == '.zip':
            return self._extract_zip(archive_path, extract_dir)
        elif extension in ['.tar', '.gz', '.tgz'] or archive_path.name.endswith('.tar.gz'):
            return self._extract_tar(archive_path, extract_dir)
        elif extension == '.7z':
            return self._extract_7z(archive_path, extract_dir)
        elif extension == '.rar':
            return self._extract_rar(archive_path, extract_dir)
        else:
            return {
                'success': False,
                'files': [],
                'error': f'Неподдерживаемый формат: {extension}'
            }

    def _extract_zip(self, archive_path: Path, extract_dir: Path) -> Dict:
        """Распаковка ZIP архива с правильной обработкой кодировки"""
        import zipfile

        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # Извлекаем файлы с правильной кодировкой имен
                for member in zip_ref.namelist():
                    # Пробуем определить правильную кодировку для имени файла
                    try:
                        # Сначала пробуем CP866 (стандарт для русской Windows)
                        filename = member.encode('cp437').decode('cp866')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        try:
                            # Если не получилось, пробуем UTF-8
                            filename = member.encode('cp437').decode('utf-8')
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            # Если и это не получилось, используем оригинальное имя
                            filename = member

                    # Извлекаем файл с правильным именем
                    source = zip_ref.open(member)
                    target_path = extract_dir / filename

                    # Создаем директории если нужно
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Записываем содержимое
                    with open(target_path, 'wb') as target:
                        target.write(source.read())

            files = list(extract_dir.rglob('*'))
            files = [f for f in files if f.is_file()]

            return {
                'success': True,
                'files': files,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'files': [],
                'error': str(e)
            }

    def _extract_tar(self, archive_path: Path, extract_dir: Path) -> Dict:
        """Распаковка TAR/GZ архива"""
        import tarfile

        try:
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_dir)

            files = list(extract_dir.rglob('*'))
            files = [f for f in files if f.is_file()]

            return {
                'success': True,
                'files': files,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'files': [],
                'error': str(e)
            }

    def _extract_7z(self, archive_path: Path, extract_dir: Path) -> Dict:
        """Распаковка 7Z архива"""

        # Primary: py7zr
        if self.has_py7zr:
            try:
                import py7zr
                with py7zr.SevenZipFile(archive_path, 'r') as archive:
                    archive.extractall(extract_dir)

                files = list(extract_dir.rglob('*'))
                files = [f for f in files if f.is_file()]

                return {
                    'success': True,
                    'files': files,
                    'error': None
                }
            except Exception as e:
                logger.warning(f"py7zr failed: {e}, trying patool")

        # Fallback: patool
        if self.has_patool:
            return self._extract_with_patool(archive_path, extract_dir)

        return {
            'success': False,
            'files': [],
            'error': 'Нет доступных библиотек для .7z'
        }

    def _extract_rar(self, archive_path: Path, extract_dir: Path) -> Dict:
        """Распаковка RAR архива"""

        # Primary: rarfile
        if self.has_rarfile:
            try:
                import rarfile
                with rarfile.RarFile(archive_path, 'r') as rar_ref:
                    rar_ref.extractall(extract_dir)

                files = list(extract_dir.rglob('*'))
                files = [f for f in files if f.is_file()]

                return {
                    'success': True,
                    'files': files,
                    'error': None
                }
            except Exception as e:
                logger.warning(f"rarfile failed: {e}, trying patool")

        # Fallback: patool
        if self.has_patool:
            return self._extract_with_patool(archive_path, extract_dir)

        return {
            'success': False,
            'files': [],
            'error': 'Нет доступных библиотек для .rar'
        }

    def _extract_with_patool(self, archive_path: Path, extract_dir: Path) -> Dict:
        """Универсальная распаковка через patool"""
        try:
            import patoolib
            patoolib.extract_archive(str(archive_path), outdir=str(extract_dir))

            files = list(extract_dir.rglob('*'))
            files = [f for f in files if f.is_file()]

            return {
                'success': True,
                'files': files,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'files': [],
                'error': str(e)
            }

    # === Обработка содержимого ===

    def _process_extracted_files(
        self,
        extracted_files: List[Path],
        temp_dir: Path,
        output_dir: Path,
        depth: int,
        archive_hashes: Set[str]
    ) -> Dict:
        """Обрабатывает извлеченные файлы"""

        results = {
            'converted': [],
            'skipped': [],
            'errors': [],
            'nested_archives': []
        }

        for file_path in extracted_files:
            relative_path = file_path.relative_to(temp_dir)

            # Проверяем, является ли файл архивом
            if self.can_convert(file_path):
                # Это вложенный архив
                nested_output_path = output_dir / relative_path.parent / f"{file_path.name}.md"

                try:
                    success = self._convert_with_depth(
                        file_path,
                        nested_output_path,
                        depth + 1,
                        archive_hashes.copy()  # Передаем копию
                    )

                    results['nested_archives'].append({
                        'file': relative_path,
                        'success': success
                    })
                except Exception as e:
                    logger.error(f"Ошибка обработки вложенного архива {file_path.name}: {e}")
                    results['errors'].append({
                        'file': relative_path,
                        'error': str(e)
                    })

            else:
                # Обычный файл - ищем конвертер
                converter = self._find_converter(file_path)

                if converter:
                    # Создаем путь для MD файла
                    md_path = output_dir / relative_path.parent / f"{file_path.name}.md"

                    try:
                        success = converter.convert_safe(file_path, md_path)

                        if success:
                            results['converted'].append({
                                'file': relative_path,
                                'converter': converter.__class__.__name__
                            })
                        else:
                            results['errors'].append({
                                'file': relative_path,
                                'error': 'Конвертация не удалась'
                            })
                    except Exception as e:
                        results['errors'].append({
                            'file': relative_path,
                            'error': str(e)
                        })
                else:
                    # Нет подходящего конвертера
                    results['skipped'].append({
                        'file': relative_path,
                        'reason': 'Нет конвертера'
                    })

        return results

    def _find_converter(self, file_path: Path) -> Optional[FileConverter]:
        """Находит подходящий конвертер для файла"""
        for converter in self.converters_registry:
            if converter.can_convert(file_path):
                return converter
        return None

    # === Создание индексного файла ===

    def _create_index_file(
        self,
        archive_path: Path,
        output_path: Path,
        temp_dir: Path,
        extracted_files: List[Path],
        processing_result: Dict,
        depth: int
    ):
        """Создает индексный MD файл для архива"""

        # Вычисляем статистику
        total_files = len(extracted_files)
        total_size = sum(f.stat().st_size for f in extracted_files if f.exists())

        # Создаем метаданные
        metadata = self._create_metadata(
            archive_path,
            total_files,
            total_size,
            depth
        )

        # Создаем содержимое
        content_sections = []
        content_sections.append(metadata)

        # Секция "Содержимое архива"
        content_sections.append("## Содержимое архива\n")

        # Конвертированные файлы
        converted_files = processing_result['converted']
        if converted_files:
            content_sections.append(f"### Конвертированные файлы ({len(converted_files)})\n")
            for item in converted_files[:50]:  # Показываем первые 50
                file_path = item['file']
                md_link = f"{output_path.stem}_extracted/{file_path}.md"
                content_sections.append(f"- `{file_path}` → [{file_path}.md]({md_link})\n")
            if len(converted_files) > 50:
                content_sections.append(f"\n_... и еще {len(converted_files) - 50} файлов_\n")
            content_sections.append("\n")

        # Вложенные архивы
        nested_archives = processing_result['nested_archives']
        if nested_archives:
            content_sections.append(f"### Вложенные архивы ({len(nested_archives)})\n")
            for item in nested_archives:
                file_path = item['file']
                status = "✅" if item['success'] else "❌"
                md_link = f"{output_path.stem}_extracted/{file_path}.md"
                content_sections.append(f"- {status} `{file_path}` → [{file_path}.md]({md_link})\n")
            content_sections.append("\n")

        # Пропущенные файлы
        skipped_files = processing_result['skipped']
        if skipped_files:
            content_sections.append(f"### Пропущенные файлы ({len(skipped_files)})\n")
            for item in skipped_files[:20]:  # Показываем первые 20
                file_path = item['file']
                reason = item.get('reason', 'Неизвестная причина')
                content_sections.append(f"- `{file_path}` - {reason}\n")
            if len(skipped_files) > 20:
                content_sections.append(f"\n_... и еще {len(skipped_files) - 20} файлов_\n")
            content_sections.append("\n")

        # Ошибки
        errors = processing_result['errors']
        if errors:
            content_sections.append(f"### Ошибки обработки ({len(errors)})\n")
            for item in errors[:20]:  # Показываем первые 20
                file_path = item['file']
                error = item.get('error', 'Неизвестная ошибка')
                content_sections.append(f"- ❌ `{file_path}` - {error}\n")
            if len(errors) > 20:
                content_sections.append(f"\n_... и еще {len(errors) - 20} ошибок_\n")
            content_sections.append("\n")

        # Дерево файлов (упрощенное)
        content_sections.append("## Структура архива\n\n")
        content_sections.append("```\n")
        content_sections.append(f"{archive_path.name}/\n")
        tree_lines = self._create_file_tree(extracted_files, temp_dir)
        content_sections.extend(tree_lines)
        content_sections.append("```\n\n")

        # Статистика
        content_sections.append("## Статистика обработки\n\n")
        content_sections.append(f"- Всего файлов: {total_files}\n")
        content_sections.append(f"- Успешно конвертировано: {len(converted_files)}\n")
        content_sections.append(f"- Вложенных архивов: {len(nested_archives)}\n")
        content_sections.append(f"- Пропущено: {len(skipped_files)}\n")
        content_sections.append(f"- Ошибок: {len(errors)}\n")

        # Сохраняем
        full_content = "\n".join(content_sections)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

    def _create_error_index(self, output_path: Path, archive_path: Path, error: str):
        """Создает индексный файл с информацией об ошибке"""
        content = f"""---
source_file: {archive_path.name}
original_format: {archive_path.suffix}
error: true
converted_by: ArchiveConverter
---

# {archive_path.stem}

**Тип:** {self._get_archive_type(archive_path).upper()} архив

## ❌ Ошибка распаковки

Не удалось распаковать архив.

**Ошибка:** {error}

Возможные причины:
- Архив поврежден
- Неподдерживаемый формат
- Архив защищен паролем
- Недостаточно прав доступа
"""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _create_file_tree(self, files: List[Path], base_dir: Path, max_depth: int = 3) -> List[str]:
        """Создает упрощенное ASCII дерево файлов"""
        tree_lines = []

        # Группируем по директориям
        dirs = set()
        for file in files:
            rel_path = file.relative_to(base_dir)
            for parent in rel_path.parents:
                if parent != Path('.'):
                    dirs.add(parent)

        # Показываем только верхний уровень и несколько файлов
        shown = 0
        max_shown = 20

        for file in sorted(files):
            if shown >= max_shown:
                tree_lines.append(f"... и еще {len(files) - shown} файлов\n")
                break

            rel_path = file.relative_to(base_dir)
            depth = len(rel_path.parts) - 1
            if depth > max_depth:
                continue

            indent = "  " * depth
            tree_lines.append(f"{indent}├── {rel_path.name}\n")
            shown += 1

        return tree_lines

    def _create_metadata(
        self,
        archive_path: Path,
        total_files: int,
        total_size: int,
        depth: int
    ) -> str:
        """Создает метаданные для индексного файла"""

        metadata = f"""---
source_file: {archive_path.name}
original_format: {archive_path.suffix}
archive_type: {self._get_archive_type(archive_path)}
total_files: {total_files}
total_size: {self._format_size(total_size)}
extraction_depth: {depth}
converted_by: ArchiveConverter
---

# {archive_path.stem}

**Тип:** {self._get_archive_type(archive_path).upper()} архив
**Файлов:** {total_files}
**Размер:** {self._format_size(total_size)}
**Глубина:** {depth}

"""
        return metadata

    # === Вспомогательные методы ===

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Вычисляет MD5 хеш файла"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"Не удалось вычислить хеш для {file_path.name}: {e}")
            return ""

    def _get_archive_type(self, archive_path: Path) -> str:
        """Определяет тип архива по расширению"""
        name = archive_path.name.lower()
        if name.endswith('.tar.gz'):
            return 'tar.gz'

        ext = archive_path.suffix.lower()
        if ext == '.zip':
            return 'zip'
        elif ext in ['.tar', '.tgz']:
            return 'tar'
        elif ext == '.gz':
            return 'gzip'
        elif ext == '.7z':
            return '7z'
        elif ext == '.rar':
            return 'rar'
        else:
            return 'unknown'

    def _format_size(self, size: int) -> str:
        """Форматирует размер в читаемый вид"""
        for unit in ["Б", "КБ", "МБ", "ГБ"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"
