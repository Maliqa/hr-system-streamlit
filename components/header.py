import streamlit as st

def global_header(role: str = ""):
    col1, col2, col3 = st.columns([6, 2, 1.2])

    # === TITLE (LEFT) ===
    with col1:
        st.markdown(
            """
            <h3 style='margin-bottom:0;'>HR Management System</h3>
            <p style='color:gray; margin-top:0;'>
                Employee • Manager • HR
            </p>
            """,
            unsafe_allow_html=True
        )

    # === ROLE (MIDDLE) ===
    with col2:
        if role:
            st.markdown(
                f"""
                <div style='text-align:right; padding-top:22px;'>
                    👤 <b>{role}</b>
                </div>
                """,
                unsafe_allow_html=True
            )

    # === LOGO (RIGHT) ===
    with col3:
        st.image("assets/cistech.png", width=70)

    st.divider()
