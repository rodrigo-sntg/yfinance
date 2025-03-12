import unittest
import sys
import os

# Executar os testes
loader = unittest.TestLoader()
suite = loader.discover('tests/unit', pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)

# Imprimir resultados
print(f"\nTestes executados: {result.testsRun}")
print(f"Falhas: {len(result.failures)}")
print(f"Erros: {len(result.errors)}")

if result.failures:
    print("\n\nFALHAS:")
    for test, error in result.failures:
        print(f"{test}")
        print(f"{error}\n")

if result.errors:
    print("\n\nERROS:")
    for test, error in result.errors:
        print(f"{test}")
        print(f"{error}\n")

# Retornar código de saída apropriado
sys.exit(not result.wasSuccessful()) 