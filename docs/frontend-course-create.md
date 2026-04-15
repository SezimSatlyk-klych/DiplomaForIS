# API: создание курса и модулей (для фронтенда)

Базовый префикс: `/api/courses/`.

Авторизация: **JWT** (`Authorization: Bearer <access_token>`).

Пользователь должен быть **специалистом** с созданным профилем (`user.specialist`). Иначе сервер вернёт ошибку валидации.

---

## 1. Справочники (подписи и допустимые коды)

Перед формой запросите:

```http
GET /api/courses/choices/
```

Ответ (смысл полей):

| Ключ в ответе | Куда подставлять на фронте |
|---------------|----------------------------|
| `category` | поле `category` курса — использовать **`value`** |
| `level` | поле `level` курса — **`value`** |
| `course_tag` | массив `tags` курса — каждый элемент = **`value`** |
| `material_type` | поле `material_type` модуля — **`value`** |

Каждый элемент справочника: `{ "value": "...", "label": "..." }`. В теле запросов отправляйте только строки **`value`**.

### Допустимые `value` (на случай офлайна)

**`category`:**  
`autism`, `speech_therapy`, `adhd`, `sensory_processing`, `social_development`, `physical_therapy`, `behavioral_support`, `learning_disabilities`

**`level`:**  
`beginner`, `intermediate`, `advanced`

**`material_type` (модуль):**  
`article`, `pdf`, `video`

**`tags` (коды из `course_tag`):**  
`to_parents`, `self_regulation`, `logical_thinking`, `learning_through_play`, `for_children`, `easy_start`, `speech_therapy_work`, `social_skills_start`, `with_parent_participation`, `speech_understanding`, `gradual_development`, `structured_classes`, `memory`, `intensive_course`

---

## 2. Создание курса

```http
POST /api/courses/
Content-Type: multipart/form-data
```

### Обязательные поля курса

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | string | Название |
| `description` | string | Описание |
| `category` | string | Код из `choices.category[].value` |
| `level` | string | Код из `choices.level[].value` |
| `price` | string/number | Десятичное, до 2 знаков (например `12000` или `12000.50`) |
| `duration` | integer | Длительность в **часах** |
| `preview_image` | file | Картинка превью |

### Необязательные поля курса

| Поле | Тип | Описание |
|------|-----|----------|
| `learning_outcomes` | string | Чему научатся; можно пустая строка |
| `tags` | массив строк | Коды тэгов; см. раздел про multipart ниже |
| `modules` | вложенные поля | Модули в одном запросе; см. раздел 4 |

Поля **`id`** и **`specialist`** не передаются: `id` приходит в ответе, специалист определяется по токену.

### Ответ

Тело — объект курса в том же составе полей, что и сериализатор (включая `id`, `modules` с `id` и `created_at` у модулей).

---

## 3. Модуль: поля

Используются и при вложении в `POST /api/courses/`, и при отдельном создании (раздел 5).

| Поле | Обязательно | Тип | Описание |
|------|-------------|-----|----------|
| `title` | да | string | Название модуля |
| `description` | нет | string | Можно пусто |
| `material_type` | да | string | `article` \| `pdf` \| `video` |
| `file` | да | file | Файл материала (статья/PDF/видео — по типу) |

Поля только для ответа: `id`, `created_at`.

---

## 4. Один запрос: курс + модули (`multipart/form-data`)

Django REST Framework ожидает **плоские** имена полей с индексами для списков.

### Тэги `tags`

Вариант A — несколько полей с **одинаковым** именем `tags` (удобно для `FormData`):

```js
formData.append('tags', 'for_children');
formData.append('tags', 'easy_start');
```

Вариант B — индексная форма: `tags[0]`, `tags[1]`, …

### Модули `modules`

Для модуля с индексом `i` (0, 1, 2, …):

- `modules[i]title`
- `modules[i]description` (можно опустить или оставить пустым)
- `modules[i]material_type`
- `modules[i]file` — файл

Пример имён для двух модулей:

- `modules[0]title`, `modules[0]material_type`, `modules[0]file`
- `modules[1]title`, `modules[1]description`, `modules[1]material_type`, `modules[1]file`

Остальные поля курса — как обычные ключи: `title`, `description`, `category`, `level`, `price`, `duration`, `preview_image`, `learning_outcomes`.

### Пример (Fetch)

```js
const formData = new FormData();
formData.append('title', 'Курс моторной сферы');
formData.append('description', 'Развиваем координацию.');
formData.append('learning_outcomes', 'Базовые упражнения дома.');
formData.append('category', 'autism');
formData.append('level', 'beginner');
formData.append('price', '12000.00');
formData.append('duration', '12');
formData.append('preview_image', previewFile); // File из <input type="file">

formData.append('tags', 'for_children');
formData.append('tags', 'memory');

formData.append('modules[0]title', 'Введение');
formData.append('modules[0]material_type', 'video');
formData.append('modules[0]file', module0File);

formData.append('modules[1]title', 'Материалы');
formData.append('modules[1]description', 'PDF с заданиями');
formData.append('modules[1]material_type', 'pdf');
formData.append('modules[1]file', module1File);

await fetch('/api/courses/', {
  method: 'POST',
  headers: { Authorization: `Bearer ${accessToken}` },
  body: formData,
});
```

Не задавайте вручную заголовок `Content-Type` для `FormData` — браузер добавит boundary.

---

## 5. Два шага: сначала курс, потом модули

Если так удобнее UI или проще отладка:

1. **`POST /api/courses/`** — только поля курса + `preview_image` (без `modules` или с пустым списком модулей).
2. Для каждого модуля: **`POST /api/courses/{course_id}/modules/`** с `multipart/form-data` и полями `title`, `description`, `material_type`, `file`.

`course_id` — из ответа шага 1 (`id`).

---

## 6. Чистый JSON (без файлов)

Создать курс **только через** `application/json` **нельзя**, если требуется загрузить `preview_image`: поле обязательно на бэкенде.

JSON подходит для **частичного обновления** (PATCH), когда не меняете картинку и не трогаете файлы модулей. Для тел с вложенными `modules` и файлами снова нужен **multipart** с теми же соглашениями об именах полей.

---

## 7. Обновление курса и замена модулей

```http
PUT /api/courses/{id}/
PATCH /api/courses/{id}/
```

- Тот же набор полей, что при создании (с учётом multipart, если есть файлы).
- Если в теле передан ключ **`modules`** (в multipart — те же `modules[i]…`), список модулей **полностью заменяется**: старые записи удаляются, создаются новые из массива.
- Если при PATCH **не** передавать `modules`, существующие модули **не** меняются.

---

## 8. Ошибки

- Нет профиля специалиста — сообщение вида «Сначала создайте профиль специалиста…».
- Неверный код `category` / `level` / тэг / `material_type` — ошибки валидации по соответствующим полям.
- Не передан обязательный файл или строковое поле — стандартные ошибки DRF по полям.

---

## 9. OpenAPI

Интерактивная схема: эндпоинт документации проекта (Swagger / Redoc), теги **`courses`** и **`course-modules`**.
