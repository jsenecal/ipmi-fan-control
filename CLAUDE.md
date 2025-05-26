# Testing Lessons Learned

## PID Controller Test Best Practices
- For tests involving mathematical boundaries, use `>=` instead of `>` when comparing with boundary values
- When testing functions with rate limiting, set up the necessary initial state (like `initialized=True`, `last_output=value`, etc.)
- When testing complex algorithms, test various distinct cases separately (below setpoint, at setpoint, above setpoint)
- Set up mock time for PID tests to have deterministic behavior

## Mock Testing Techniques
- Use `patch.object()` to mock specific methods of a class
- When mocking a method that's called multiple times with different arguments, use `side_effect` instead of `return_value`
- Use `verify=False` on object initialization to avoid unintended real connections during tests

## CLI Testing Improvements
- When testing a CLI that imports external dependencies, mock at the package level where the import happens
- Use `assert_called()` instead of `assert_called_once()` for more flexible testing when exact call count is not critical
- Mock commands that would interact with external systems (like subprocess calls)

## Module Import Mocking
- Prefer patching module-level imports over function-level imports for consistent behavior
- Mock imported classes before importing the module that uses them
- When testing modules that dynamically choose implementations based on conditions, patch the condition checks

## Test Stability Techniques
- Standardize indentation and whitespace in test fixture text to match parsing expectations
- Don't rely on leading/trailing whitespace in text fixtures if the code trims it
- For command outputs that vary, mock specific command patterns and return appropriate outputs with a side effect function

## Error Handling
- Ensure tests verify both success and error paths
- Test that your error handling code behaves correctly with appropriate mocks

## Coverage Guidelines
- Aim for 90%+ coverage of critical code like algorithms (PID controller)
- For I/O and UI code, 40-50% coverage may be acceptable if main paths are covered
- Integration tests should verify the correct interaction between components

## Git Commit Guidelines
- Use conventional commit prefixes: feat:, chore:, fix: where applicable
- Write commit messages as bullet points describing what was added/changed
- No attributions or co-authored-by lines
- Keep messages concise and descriptive