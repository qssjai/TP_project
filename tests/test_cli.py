from sipl.cli import main


def test_chomsky_command_prints_steps_and_grammar(examples_dir, capsys):
    code = main(["cfg", "chomsky", str(examples_dir / "pr4_variant1.txt")])
    output = capsys.readouterr().out
    assert code == 0
    assert "-- Заміна терміналів" in output
    assert "B′ → b" in output


def test_no_steps_flag(examples_dir, capsys):
    code = main(["cfg", "clean", str(examples_dir / "pr4_book_example.txt"), "--no-steps"])
    output = capsys.readouterr().out
    assert code == 0
    assert "--" not in output
    assert "D →" not in output


def test_missing_file_returns_error_code(capsys):
    assert main(["cfg", "clean", "no_such_file.txt"]) == 2
    assert "Не вдалося прочитати файл" in capsys.readouterr().err


def test_invalid_grammar_returns_error_code(tmp_path, capsys):
    path = tmp_path / "bad.txt"
    path.write_text("S a b", encoding="utf-8")
    assert main(["cfg", "clean", str(path)]) == 1
    assert "Помилка в граматиці" in capsys.readouterr().err
