import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL")
API_KEY = os.getenv("APP_API_KEY", "")
HEADERS = {"x-api-key": API_KEY}

st.set_page_config(
    page_title="PDF Ассистент",
    page_icon="📄",
    layout="centered"
)

st.title("📄 PDF Ассистент")

@st.dialog("Внимание: Сброс данных")
def confirm_reset():
    st.warning("Загрузка нового файла приведет к очистке текущего чата и удалению старой коллекции в базе данных. Вы уверены?")
    col1, col2 = st.columns(2)
    
    if col1.button("Да, очистить", use_container_width=True, type="primary"):
        try:
            # Вызываем очистку через API
            response = requests.delete(f"{API_URL}/clear", headers=HEADERS)
            if response.status_code == 200:
                st.session_state.messages = []
                st.session_state.file_processed = False
                st.rerun()
            else:
                st.error("Ошибка при очистке")
        except Exception:
            st.error("Сервер недоступен")
            
    if col2.button("Отмена", use_container_width=True):
        st.rerun()

# --- Sidebar: загрузка PDF ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_processed" not in st.session_state:
    st.session_state.file_processed = False

# --- Sidebar: управление документом ---
with st.sidebar:
    st.header("Управление документом")
    
    # Блок загрузки показывается только если файл еще не обработан
    if not st.session_state.file_processed:
        uploaded_file = st.file_uploader("Выберите PDF файл", type=["pdf"])

        if uploaded_file is not None:
            if st.button("Загрузить", use_container_width=True):
                with st.spinner("Обрабатываю PDF..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/upload",
                            files={"file": (uploaded_file.name, uploaded_file, "application/pdf")},
                            headers=HEADERS
                        )
                        if response.status_code == 200:
                            data = response.json()
                            st.success(f"✅ Загружено!")
                            # Активируем флаг, чтобы скрыть это меню
                            st.session_state.file_processed = True
                            st.rerun() 
                        else:
                            st.error(f"Ошибка: {response.json().get('detail')}")
                    except Exception as e:
                        st.error(f"Не удалось подключиться к серверу")
    else:
        # Если файл загружен, показываем статус и кнопку сброса
        st.info("✅ Документ загружен и готов к работе.")
        if st.button("🔄 Загрузить другой файл", use_container_width=True):
            confirm_reset()

    st.divider()
    
    if st.button("🗑 Очистить всё", use_container_width=True):
        with st.spinner("Очистка данных..."):
            try:
                
                response = requests.delete(f"{API_URL}/clear", headers=HEADERS)
                
                if response.status_code == 200:
                    st.session_state.messages = []
                    st.session_state.file_processed = False
                    st.success("История и база данных очищены!")
                    st.rerun()
                else:
                    st.error("Ошибка при очистке базы данных на сервере")
            except Exception as e:
                st.error("Сервер недоступен")

# --- История сообщений ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            with st.expander("📚 Источники"):
                for src in msg["sources"]:
                    st.caption(f"Страница {src['page']} | Score: {src['score']:.2f}")
                    st.text(src["text"][:200] + "...")
                    st.divider()

# --- Поле ввода ---
if query := st.chat_input("Задайте вопрос по документу..."):
    # Показываем вопрос
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Запрос к FastAPI
    with st.chat_message("assistant"):
        with st.spinner("Думаю..."):
            try:
                response = requests.post(
                    f"{API_URL}/ask",
                    params={"query": query},
                    headers=HEADERS
                )
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])

                    st.markdown(answer)
                    if sources:
                        with st.expander("📚 Источники"):
                            for src in sources:
                                st.caption(f"Страница {src['page']} | Score: {src['score']:.2f}")
                                st.text(src["text"][:200] + "...")
                                st.divider()

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    error = response.json().get("detail", "Неизвестная ошибка")
                    st.error(f"Ошибка: {error}")

            except Exception as e:
                st.error(f"Не удалось подключиться к серверу")



#streamlit run streamlit_app.py