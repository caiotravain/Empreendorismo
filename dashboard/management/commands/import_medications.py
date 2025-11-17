"""
Django management command to import medications from CSV file
"""
import csv
import os
import unicodedata
from django.core.management.base import BaseCommand
from django.conf import settings
from dashboard.models import Medication


class Command(BaseCommand):
    help = 'Import valid medications from CSV file. Maps NOME_PRODUTO -> name and PRINCIPIO_ATIVO -> description'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='databases/DADOS_ABERTOS_MEDICAMENTOS.csv',
            help='Path to the CSV file (relative to project root)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually saving to database'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        
        # Get the full path to the CSV file
        project_root = settings.BASE_DIR
        csv_path = os.path.join(project_root, csv_file)
        
        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f'CSV file not found: {csv_path}')
            )
            return
        
        self.stdout.write(f'Reading CSV file: {csv_path}')
        
        imported_count = 0
        skipped_count = 0
        duplicate_count = 0
        invalid_count = 0
        
        try:
            # Try different encodings - Brazilian files often use Latin-1 or Windows-1252
            encodings = ['latin-1', 'windows-1252', 'utf-8', 'cp1252']
            used_encoding = None
            
            # Detect the correct encoding
            for encoding in encodings:
                try:
                    with open(csv_path, 'r', encoding=encoding, errors='replace') as f:
                        # Test read first line to see if encoding works
                        test_line = f.readline()
                        if test_line:
                            used_encoding = encoding
                            break
                except Exception:
                    continue
            
            if used_encoding is None:
                self.stdout.write(
                    self.style.ERROR('Could not read CSV file with any supported encoding')
                )
                return
            
            self.stdout.write(f'Using encoding: {used_encoding}')
            
            # Open with the working encoding
            with open(csv_path, 'r', encoding=used_encoding, errors='replace') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                # Track names we've seen in this import to avoid duplicates within the file
                seen_names = set()
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
                    try:
                        # Get the medication name and active principle
                        nome_produto = row.get('NOME_PRODUTO', '').strip()
                        principio_ativo = row.get('PRINCIPIO_ATIVO', '').strip()
                        situacao = row.get('SITUACAO_REGISTRO', '').strip()
                        # Skip if no name
                        if not nome_produto:
                            invalid_count += 1
                            continue
                        



                        # Normalize unicode to handle encoding issues with accented characters
                        situacao_normalized = unicodedata.normalize('NFKD', situacao.upper())
                        situacao_normalized = ''.join(c for c in situacao_normalized if not unicodedata.combining(c))
                        valid_status = unicodedata.normalize('NFKD', 'VÁLIDO')
                        valid_status = ''.join(c for c in valid_status if not unicodedata.combining(c))
                        
                        # Only process valid medications
                        if situacao_normalized != valid_status:
                            skipped_count += 1
                            continue

                        # Remove quotes if present
                        nome_produto = nome_produto.strip('"')
                        principio_ativo = principio_ativo.strip('"')
                        
                        # Normalize the names to ensure proper encoding (NFC preserves accents properly)
                        nome_produto = unicodedata.normalize('NFC', nome_produto)
                        if principio_ativo:
                            principio_ativo = unicodedata.normalize('NFC', principio_ativo)
                        
                        # Check for duplicates within the file (case-insensitive)
                        nome_lower = nome_produto.lower()
                        if nome_lower in seen_names:
                            duplicate_count += 1
                            continue
                        
                        # Check if medication with same name already exists in database
                        if Medication.objects.filter(name__iexact=nome_produto).exists():
                            duplicate_count += 1
                            continue
                        
                        # Add to seen names
                        seen_names.add(nome_lower)
                        
                        # Create medication
                        if not dry_run:
                            Medication.objects.create(
                                name=nome_produto,
                                description=principio_ativo if principio_ativo else None
                            )
                        
                        imported_count += 1
                        
                        # Progress indicator every 1000 records
                        if imported_count % 1000 == 0:
                            self.stdout.write(f'Processed {imported_count} medications...')
                    
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'Error processing row {row_num}: {str(e)}')
                        )
                        invalid_count += 1
                        continue
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading CSV file: {str(e)}')
            )
            return
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Import Summary:'))
        self.stdout.write(f'  Imported: {imported_count}')
        self.stdout.write(f'  Duplicates skipped: {duplicate_count}')
        self.stdout.write(f'  Invalid status skipped: {skipped_count}')
        self.stdout.write(f'  Invalid rows: {invalid_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No data was saved to database'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully imported {imported_count} medications!'))

