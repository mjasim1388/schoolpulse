"""
Shared UI helpers for SchoolPulse.
"""

import streamlit as st


def _html(s: str):
    """Flatten multi-line HTML so it renders as HTML, not text."""
    return " ".join(line.strip() for line in s.splitlines() if line.strip())


def html(s: str):
    """Render HTML safely — flattens whitespace first."""
    st.markdown(_html(s), unsafe_allow_html=True)


def make_selectboxes_readonly():
    """
    Make every Streamlit selectbox's input readonly so users can only
    pick from the list — they cannot type to filter. Clicks still work:
    the whole box opens the dropdown as normal.

    Uses a MutationObserver so it also catches newly rendered dropdowns.
    """
    st.markdown(_html("""
        <script>
        (function() {
            const doc = window.parent.document;

            function applyReadonly() {
                doc.querySelectorAll('[data-baseweb="select"] input').forEach(function(inp) {
                    if (inp.getAttribute('readonly') !== 'readonly') {
                        inp.setAttribute('readonly', 'readonly');
                    }
                    if (inp.style.caretColor !== 'transparent') {
                        inp.style.caretColor = 'transparent';
                    }
                });
            }

            applyReadonly();

            if (!window.__spSelectObserver) {
                window.__spSelectObserver = new MutationObserver(function() {
                    applyReadonly();
                });
                window.__spSelectObserver.observe(doc.body, {
                    childList: true,
                    subtree: true
                });
            }
        })();
        </script>
    """), unsafe_allow_html=True)