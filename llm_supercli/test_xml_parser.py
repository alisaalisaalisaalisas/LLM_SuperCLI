"""Quick test for XMLStyleParser."""
from llm_supercli.prompts.tools import XMLStyleParser

p = XMLStyleParser()
print('Name:', p.name)
print('Priority:', p.priority)

# Test basic parsing
content = '''<function_calls><invoke name="read_file"><parameter name="path">test.txt</parameter></invoke></function_calls>'''
result = p.parse(content)
print('Result:', result)

# Test multiple parameters
content2 = '''<function_calls><invoke name="write_file"><parameter name="path">out.txt</parameter><parameter name="content">Hello World</parameter></invoke></function_calls>'''
result2 = p.parse(content2)
print('Result2:', result2)

# Test standalone invoke
content3 = '''<invoke name="list_files"><parameter name="directory">/home</parameter></invoke>'''
result3 = p.parse(content3)
print('Result3:', result3)

print('All tests passed!')
