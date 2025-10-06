import sys

print("Python is working!")
print(f"Python version: {sys.version}")
with open("test_output.txt", "w") as f:
    f.write("This is a test output file.\n")
    f.write(f"Python version: {sys.version}\n")
print("Created test_output.txt file")
