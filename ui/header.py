import streamlit as st

def page_header(title, icon="🏢", logo_path="assets/cistech.png"):
    col1, col2 = st.columns([8, 2])

    with col1:
        st.markdown(
            f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 14px;
            ">
                <div style="font-size:42px;">{icon}</div>
                <h1 style="margin:0;">{title}</h1>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: flex-end;
                align-items: center;
                height: 100%;
            ">
                <img src="{logo_path}" style="height:42px;" />
            </div>
            """,
            unsafe_allow_html=True
        )
