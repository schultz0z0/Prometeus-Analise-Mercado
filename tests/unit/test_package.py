from prometeus import __descriptor__, __product__, __vendor__, __version__


def test_package_metadata() -> None:
    assert __version__ == "0.1.0"
    assert __product__ == "Prometeus"
    assert __descriptor__ == "Inteligência para Produtos Educacionais"
    assert __vendor__ == "Agência Prometeus"
