import os
import csv
import tempfile
import pytest
import subprocess
from pathlib import Path


class TestEvernoteIntegration:
    """Integration tests for the Evernote import workflow."""

    def test_enex_to_csv_conversion(self):
        """Test the end-to-end conversion of an ENEX file to CSV."""
        # Get the path to the sample ENEX file
        sample_enex = Path(__file__).parent.parent / "samples" / "sample.enex"
        assert sample_enex.exists(), f"Sample ENEX file not found at {sample_enex}"

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_output:
            output_csv = temp_output.name

        try:
            # Run the conversion command
            cmd = [
                "python", "raindrop_import.py", "evernote",
                "--input-file", str(sample_enex),
                "--output-file", output_csv,
                "--use-markdown"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check that the command succeeded
            assert result.returncode == 0, f"Command failed with output: {result.stderr}"
            
            # Check that the output file exists
            assert os.path.exists(output_csv), f"Output file not created at {output_csv}"
            
            # Check the content of the output file
            with open(output_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # Check that we have the expected number of rows
                assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
                
                # Check the content of the first row
                assert rows[0]["title"] == "Sample Note 1", f"Unexpected title: {rows[0]['title']}"
                assert "This is a sample note" in rows[0]["description"], f"Unexpected description: {rows[0]['description']}"
                assert rows[0]["url"] == "http://example.com/note1", f"Unexpected URL: {rows[0]['url']}"
                assert "sample" in rows[0]["tags"], f"Expected 'sample' tag in {rows[0]['tags']}"
                assert "test" in rows[0]["tags"], f"Expected 'test' tag in {rows[0]['tags']}"
                
                # Check the content of the second row
                assert rows[1]["title"] == "Sample Note 2", f"Unexpected title: {rows[1]['title']}"
                assert "This is another sample note" in rows[1]["description"], f"Unexpected description: {rows[1]['description']}"
                assert rows[1]["url"] == "http://example.com/note2", f"Unexpected URL: {rows[1]['url']}"
                assert "sample" in rows[1]["tags"], f"Expected 'sample' tag in {rows[1]['tags']}"
        finally:
            # Clean up the temporary file
            if os.path.exists(output_csv):
                os.unlink(output_csv)

    def test_enex_to_csv_dry_run(self):
        """Test the dry-run mode of the ENEX to CSV conversion."""
        # Get the path to the sample ENEX file
        sample_enex = Path(__file__).parent.parent / "samples" / "sample.enex"
        assert sample_enex.exists(), f"Sample ENEX file not found at {sample_enex}"

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_output:
            output_csv = temp_output.name

        try:
            # Run the conversion command with dry-run
            cmd = [
                "python", "raindrop_import.py", "evernote",
                "--input-file", str(sample_enex),
                "--output-file", output_csv,
                "--use-markdown",
                "--dry-run"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check that the command succeeded
            assert result.returncode == 0, f"Command failed with output: {result.stderr}"
            
            # Check that the output file was not created (or is empty if it exists)
            if os.path.exists(output_csv):
                assert os.path.getsize(output_csv) == 0, f"Output file should be empty in dry-run mode"
        finally:
            # Clean up the temporary file
            if os.path.exists(output_csv):
                os.unlink(output_csv)