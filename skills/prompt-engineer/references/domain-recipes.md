# Optional domain recipes

Examples apply only within the current order and core authority.

## EARS Methodology

### Origin
**EARS** = Easy Approach to Requirements Syntax
Developed by Rolls-Royce for aerospace requirements.

### Five Patterns

#### 1. Ubiquitous (Always)
```
The system shall <action>
```
**When:** Requirement is always active, unconditional.
**Example:** `The system shall encrypt all data at rest`

#### 2. Event-Driven (On event)
```
When <trigger event>, the system shall <action>
```
**When:** Action in response to a specific event.
**Example:** `When user clicks login, the system shall validate credentials`

#### 3. State-Driven (In state)
```
While <system state>, the system shall <action>
```
**When:** Action while system is in a specific state.
**Example:** `While offline, the system shall queue requests locally`

#### 4. Conditional (Conditional)
```
If <condition>, the system shall <action>
```
**When:** Action when condition is met.
**Example:** `If user role is admin, the system shall show settings panel`

#### 5. Unwanted Behavior (Unwanted)
```
If <unwanted condition>, the system shall prevent <unwanted action>
```
**When:** Preventing unwanted behavior.
**Example:** `If login fails 5 times, the system shall lock account for 30 minutes`

---
