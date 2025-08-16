def test_home_page():
    from streamlit.testing.v1.app_test import AppTest

    at = AppTest.from_file("src/app/ui/streamlit_app.py").run()
    assert not at.exception
    at.button[0].click().run()  # Click the button to increment the counter
    assert at.button[0].value is True
    assert at.session_state.counter == 1
