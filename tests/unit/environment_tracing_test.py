from pgctl import environment_tracing


def it_finds_the_correct_processes(tmp_path):
    proc = tmp_path / 'proc'
    proc.mkdir()

    pid100 = proc / '100'
    pid100.mkdir()
    (pid100 / 'environ').write_bytes(b'A=1\x00B=2\x00C=3\x00')

    pid200 = proc / '200'
    pid200.mkdir()
    (pid200 / 'environ').write_bytes(b'  \x00B=3\x00')

    pid300 = proc / '300'
    pid300.mkdir()
    (pid300 / 'environ').write_bytes(b'  \x00A=1\x00B=2\x00')

    (proc / 'not-a-pid').mkdir()

    assert environment_tracing.find_processes_with_environ({b'A': b'1'}, str(proc)) == {100, 300}
    assert environment_tracing.find_processes_with_environ({b'B': b'2'}, str(proc)) == {100, 300}
    assert environment_tracing.find_processes_with_environ({b'B': b'3'}, str(proc)) == {200}
    assert environment_tracing.find_processes_with_environ({b'C': b'3'}, str(proc)) == {100}
    assert environment_tracing.find_processes_with_environ({b'A': b'1', b'C': b'3'}, str(proc)) == {100}
    assert environment_tracing.find_processes_with_environ({b'A': b'1', b'B': b'3'}, str(proc)) == set()
