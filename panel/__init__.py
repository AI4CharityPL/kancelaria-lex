"""Panel spraw sądowych — kancelaria-lex.

Moduły wewnątrz pakietu importują się nawzajem płasko (`import baza`),
opierając się na `sys.path`, który ustawia `serwer.py` przy starcie.
Dzięki temu działa i `python panel/serwer.py`, i `kancelaria-lex`
z instalacji edytowalnej.
"""

__version__ = "0.1.0"
