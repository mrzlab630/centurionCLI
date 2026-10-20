# refactorer optional domain recipes

Select only the technique needed for the approved question. Examples and section
numbers are reference material, never an instruction to perform all phases or
expand scope. Core authority, current project facts and mission budget govern.

## Clean Code Dimensions (7)

### 1. Meaningful Naming
```typescript
// ❌ BAD
const d = new Date();
const arr = users.filter(u => u.a);
function proc(x) { }

// ✅ GOOD
const createdAt = new Date();
const activeUsers = users.filter(user => user.isActive);
function processPayment(order) { }
```

**Rules:**
- Names reveal intention
- Avoid abbreviations (except common ones: id, url, api)
- Boolean: `is`, `has`, `can`, `should` prefix
- Functions: verb + noun (`getUser`, `validateEmail`)
- Classes: noun (PascalCase)
- Constants: SCREAMING_SNAKE_CASE

### 2. Small Functions (SRP)
```typescript
// ❌ BAD: Function doing too much
function processOrder(order) {
  // Validate order (20 lines)
  // Calculate totals (30 lines)
  // Apply discounts (25 lines)
  // Send notification (15 lines)
  // Update inventory (20 lines)
}

// ✅ GOOD: Single responsibility each
function processOrder(order) {
  validateOrder(order);
  const totals = calculateTotals(order);
  const finalPrice = applyDiscounts(totals, order.discounts);
  await updateInventory(order.items);
  await sendOrderNotification(order);
  return { ...order, finalPrice };
}
```

**Rules:**
- Max 50 lines per function
- Max 3 parameters (use options object for more)
- One level of abstraction per function
- Do one thing, do it well

### 3. DRY (Don't Repeat Yourself)
```typescript
// ❌ BAD: Duplicated logic
function createUser(data) {
  if (!data.email || !data.email.includes('@')) {
    throw new Error('Invalid email');
  }
  // ...
}

function updateUser(id, data) {
  if (data.email && !data.email.includes('@')) {
    throw new Error('Invalid email');
  }
  // ...
}

// ✅ GOOD: Extracted validation
function validateEmail(email: string): void {
  if (!email || !email.includes('@')) {
    throw new ValidationError('Invalid email format');
  }
}

function createUser(data) {
  validateEmail(data.email);
  // ...
}

function updateUser(id, data) {
  if (data.email) validateEmail(data.email);
  // ...
}
```

### 4. YAGNI (You Aren't Gonna Need It)
```typescript
// ❌ BAD: Premature abstraction
class AbstractUserFactoryBuilder {
  // Complex infrastructure for "future flexibility"
}

// ✅ GOOD: Simple and direct
function createUser(data: UserInput): User {
  return { id: generateId(), ...data, createdAt: new Date() };
}
```

### 5. No Magic Numbers
```typescript
// ❌ BAD
if (password.length < 8) { }
setTimeout(fn, 86400000);
if (retries > 3) { }

// ✅ GOOD
const MIN_PASSWORD_LENGTH = 8;
const ONE_DAY_MS = 24 * 60 * 60 * 1000;
const MAX_RETRIES = 3;

if (password.length < MIN_PASSWORD_LENGTH) { }
setTimeout(fn, ONE_DAY_MS);
if (retries > MAX_RETRIES) { }
```

### 6. Code Clarity
```typescript
// ❌ BAD: Nested ternaries
const status = a ? b ? 'x' : 'y' : c ? 'z' : 'w';

// ✅ GOOD: Clear logic
function getStatus(a: boolean, b: boolean, c: boolean): string {
  if (a && b) return 'x';
  if (a) return 'y';
  if (c) return 'z';
  return 'w';
}
```

### 7. Consistent Conventions
```typescript
// ❌ BAD: Mixed styles
const user_name = '';
const userEmail = '';
function GetUser() { }
function fetchuser() { }

// ✅ GOOD: Consistent
const userName = '';
const userEmail = '';
function getUser() { }
function fetchUser() { }
```

---

## Code Smells & Refactoring Patterns

### Long Method → Extract Method
```typescript
// Before
function processData(data) {
  // 100 lines of code
}

// After
function processData(data) {
  const validated = validateData(data);
  const transformed = transformData(validated);
  const result = computeResult(transformed);
  return formatOutput(result);
}
```

### Long Parameter List → Parameter Object
```typescript
// Before
function createUser(name, email, age, address, phone, role) { }

// After
interface CreateUserInput {
  name: string;
  email: string;
  age: number;
  address?: string;
  phone?: string;
  role?: UserRole;
}

function createUser(input: CreateUserInput) { }
```

### Nested Conditionals → Guard Clauses
```typescript
// Before
function processOrder(order) {
  if (order) {
    if (order.items.length > 0) {
      if (order.status === 'pending') {
        // process
      }
    }
  }
}

// After
function processOrder(order) {
  if (!order) return;
  if (order.items.length === 0) return;
  if (order.status !== 'pending') return;

  // process
}
```

### Primitive Obsession → Value Object
```typescript
// Before
function sendEmail(to: string) {
  if (!to.includes('@')) throw new Error('Invalid email');
  // send
}

// After
class Email {
  constructor(private readonly value: string) {
    if (!value.includes('@')) {
      throw new ValidationError('Invalid email format');
    }
  }

  toString(): string { return this.value; }
}

function sendEmail(to: Email) {
  // send - already validated
}
```

### Feature Envy → Move Method
```typescript
// Before: Order class accessing Cart internals
class Order {
  calculateTotal(cart: Cart) {
    let total = 0;
    for (const item of cart.items) {
      total += item.price * item.quantity;
    }
    return total;
  }
}

// After: Logic moved to Cart
class Cart {
  getTotal(): number {
    return this.items.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );
  }
}
```

### God Class → Extract Class
```typescript
// Before: User class doing everything
class User {
  // user data
  // authentication
  // email sending
  // payment processing
  // report generation
}

// After: Separated responsibilities
class User { /* user data only */ }
class AuthService { /* authentication */ }
class EmailService { /* email sending */ }
class PaymentService { /* payments */ }
class ReportService { /* reports */ }
```

---

## SOLID Principles

### S - Single Responsibility
One class = one reason to change.

### O - Open/Closed
Open for extension, closed for modification.

### L - Liskov Substitution
Subtypes can be substitutable for base types.

### I - Interface Segregation
Many specific interfaces > one general interface.

### D - Dependency Inversion
Depend on abstractions, not concretions.

---
