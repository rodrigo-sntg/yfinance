import subprocess
import sys

# Executar os testes usando subprocess
cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests/unit", "-p", "test_*.py", "-v"]
result = subprocess.run(cmd, capture_output=True, text=True)

# Salvar a saída em um arquivo
with open('test_output.txt', 'w') as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\n\nExit code: {result.returncode}")

print(f"Exit code: {result.returncode}")
print("Saída completa salva em test_output.txt") 