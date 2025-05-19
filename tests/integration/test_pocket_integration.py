import os
import csv
import tempfile
import pytest
import subprocess
from pathlib import Path


class TestPocketIntegration:
    """Integration tests for the Pocket import workflow."""

    def test_pocket_to_csv_conversion(self):
        """Test the end-to-end conversion of a Pocket HTML file to CSV."""
        # Get the path to the sample Pocket HTML file
        sample_html = Path(__file__).parent.parent / "samples" / "sample_pocket.html"
        assert sample_html.exists(), f"Sample Pocket HTML file not found at {sample_html}"

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_output:
            output_csv = temp_output.name

        try:
            # Run the conversion command
            cmd = [
                "python", "raindrop_import.py", "pocket",
                "--input-file", str(sample_html),
                "--output-file", output_csv
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
                assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
                
                # Check the content of the first row
                assert rows[0]["title"] == "Sample Article 1", f"Unexpected title: {rows[0]['title']}"
                assert rows[0]["url"] == "http://example.com/article1", f"Unexpected URL: {rows[0]['url']}"
                assert "sample" in rows[0]["tags"], f"Expected 'sample' tag in {rows[0]['tags']}"
                assert "test" in rows[0]["tags"], f"Expected 'test' tag in {rows[0]['tags']}"
                
                # Check the content of the second row
                assert rows[1]["title"] == "Sample Article 2", f"Unexpected title: {rows[1]['title']}"
                assert rows[1]["url"] == "http://example.com/article2", f"Unexpected URL: {rows[1]['url']}"
                assert "sample" in rows[1]["tags"], f"Expected 'sample' tag in {rows[1]['tags']}"
                
                # Check the content of the third row
                assert rows[2]["title"] == "Sample Article 3", f"Unexpected title: {rows[2]['title']}"
                assert rows[2]["url"] == "http://example.com/article3", f"Unexpected URL: {rows[2]['url']}"
                assert rows[2]["tags"] == "", f"Expected empty tags, got {rows[2]['tags']}"
        finally:
            # Clean up the temporary file
            if os.path.exists(output_csv):
                os.unlink(output_csv)

    def test_pocket_to_csv_dry_run(self):
        """Test the dry-run mode of the Pocket HTML to CSV conversion."""
        # Get the path to the sample Pocket HTML file
        sample_html = Path(__file__).parent.parent / "samples" / "sample_pocket.html"
        assert sample_html.exists(), f"Sample Pocket HTML file not found at {sample_html}"

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_output:
            output_csv = temp_output.name

        try:
            # Run the conversion command with dry-run
            cmd = [
                "python", "raindrop_import.py", "pocket",
                "--input-file", str(sample_html),
                "--output-file", output_csv,
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