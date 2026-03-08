# anki_builder

CLI-утилита для создания карточек Anki.

Копируешь текст из чата в буфер обмена, запускаешь команду — получаешь TSV-файл для импорта в Anki. Каждое слово автоматически обогащается через Claude API: добавляются грамматические формы, этимология, примеры и теги.

## Требования

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- `ANTHROPIC_API_KEY` в переменных окружения

## Основное использование

```bash
# Скопировать текст из чата в буфер обмена, затем:
uv run greek-anki process
```

Утилита:
1. Читает текст из буфера обмена
2. Извлекает пары греческое слово — русский перевод
3. Обогащает каждое слово (тип, склонение, этимология, примеры, теги)
4. Показывает результат и спрашивает подтверждение
5. Сохраняет в базу (`~/.greek-anki/vocabulary.db`) и экспортирует в `new-cards.tsv`

Файл `new-cards.tsv` импортируется в Anki (File → Import).

## Опции process

```bash
uv run greek-anki process -f file.txt   # читать из файла
uv run greek-anki process --stdin        # читать из stdin
uv run greek-anki process -o cards.tsv   # другой выходной файл (по умолчанию new-cards.tsv)
uv run greek-anki process -y             # без подтверждения
```

## Другие команды

```bash
uv run greek-anki stats              # статистика базы
uv run greek-anki export             # экспорт всей базы в vocabulary-export.tsv
uv run greek-anki import file.tsv    # импорт существующего TSV в базу
uv run greek-anki css                # вывести CSS для шаблона карточек в Anki
```

## Настройка карточек в Anki

При первом использовании добавь CSS в шаблон карточек:

```bash
uv run greek-anki css
```

Скопируй вывод в Anki: Browse → Cards → Styling.

## Формат карточек

- **Лицевая сторона:** греческое слово/фраза
- **Обратная сторона (HTML):** перевод, тип слова, грамматические формы, этимология, примеры
