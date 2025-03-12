import unittest
import sys
import os
from io import StringIO

# Redirecionar stdout para capturar a saída
old_stdout = sys.stdout
sys.stdout = mystdout = StringIO()

# Executar os testes
loader = unittest.TestLoader()
suite = loader.discover('tests/unit', pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)

# Restaurar stdout
sys.stdout = old_stdout

# Salvar a saída em um arquivo
with open('test_output.txt', 'w') as f:
    f.write(mystdout.getvalue())
    f.write(f"\n\nTestes executados: {result.testsRun}\n")
    f.write(f"Falhas: {len(result.failures)}\n")
    f.write(f"Erros: {len(result.errors)}\n")
    
    if result.failures:
        f.write("\n\nFALHAS:\n")
        for test, error in result.failures:
            f.write(f"{test}\n")
            f.write(f"{error}\n\n")
    
    if result.errors:
        f.write("\n\nERROS:\n")
        for test, error in result.errors:
            f.write(f"{test}\n")
            f.write(f"{error}\n\n")

print(f"Testes executados: {result.testsRun}")
print(f"Falhas: {len(result.failures)}")
print(f"Erros: {len(result.errors)}")
print("Saída completa salva em test_output.txt") 