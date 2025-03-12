#!/usr/bin/env python3
"""
Script para executar os testes da aplicação com relatório de cobertura
"""
import os
import sys
import unittest
import coverage


def run_unit_tests():
    """Executa testes unitários"""
    print("Executando testes unitários...")
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests/unit', pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()


def run_integration_tests():
    """Executa testes de integração"""
    print("\nExecutando testes de integração...")
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests/integration', pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()


def run_all_tests_with_coverage():
    """Executa todos os testes com cobertura"""
    print("Executando todos os testes com cobertura...")
    
    # Configura o coverage para medir apenas a aplicação, não os testes
    cov = coverage.Coverage(
        source=['app'],
        omit=['tests/*', '*/site-packages/*']
    )
    
    # Inicia a coleta de dados de cobertura
    cov.start()
    
    # Executa os testes
    test_loader = unittest.TestLoader()
    
    # Testes unitários
    unit_suite = test_loader.discover('tests/unit', pattern='test_*.py')
    # Testes de integração
    integration_suite = test_loader.discover('tests/integration', pattern='test_*.py')
    
    # Combina as suites
    all_tests = unittest.TestSuite([unit_suite, integration_suite])
    
    # Executa todos os testes
    result = unittest.TextTestRunner(verbosity=2).run(all_tests)
    
    # Para a coleta de dados de cobertura
    cov.stop()
    
    # Salva os resultados para uso posterior
    cov.save()
    
    # Gera relatório no terminal
    print("\nRelatório de cobertura:")
    cov.report()
    
    # Gera relatório HTML
    output_dir = 'coverage_html'
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nGerando relatório HTML em {output_dir}")
    cov.html_report(directory=output_dir)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Processa argumentos de linha de comando
        command = sys.argv[1]
        if command == 'unit':
            success = run_unit_tests()
        elif command == 'integration':
            success = run_integration_tests()
        elif command == 'all':
            success = run_all_tests_with_coverage()
        else:
            print(f"Comando desconhecido: {command}")
            print("Uso: python run_tests.py [unit|integration|all]")
            success = False
    else:
        # Sem argumentos, executa todos os testes com cobertura
        success = run_all_tests_with_coverage()
    
    # Define o código de saída
    sys.exit(0 if success else 1) 