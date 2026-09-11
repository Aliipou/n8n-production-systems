-- migrate:up

-- Fictional suppliers only. Names, Y-tunnus, IBANs, and BICs are invented
-- for the synthetic dataset. They must not match a real company.

INSERT INTO p02.suppliers (id, name, business_id, vat_id, iban, bic, active) VALUES
    (
        'a1111111-1111-4111-8111-111111111111',
        'Pohjoinen Kuutio Oy',
        '1234567-1',
        'FI12345671',
        'FI7631913000000001',
        'PHTCFIHH',
        true
    ),
    (
        'a2222222-2222-4222-8222-222222222222',
        'Satamatie Demo Ab',
        '2222222-9',
        'FI22222229',
        'FI3679988800001234',
        'STMDFIHH',
        true
    ),
    (
        'a3333333-3333-4333-8333-333333333333',
        'Keltaiset Hammasrattaat Oy',
        '3333333-8',
        'FI33333338',
        'FI4411111111111111',
        'KHRTFIHH',
        true
    ),
    (
        'a4444444-4444-4444-8444-444444444444',
        'Fiktivinen Huolto Tmi',
        '1000001-2',
        'FI10000012',
        'FI0255555555555555',
        'FKHVFIHH',
        true
    ),
    (
        'a5555555-5555-4555-8555-555555555555',
        'Lannen Testipaja Oy',
        '2000000-8',
        'FI20000008',
        'FI2112345600000785',
        'LNTPFIHH',
        false
    );

-- migrate:down

DELETE FROM p02.suppliers
WHERE id IN (
    'a1111111-1111-4111-8111-111111111111',
    'a2222222-2222-4222-8222-222222222222',
    'a3333333-3333-4333-8333-333333333333',
    'a4444444-4444-4444-8444-444444444444',
    'a5555555-5555-4555-8555-555555555555'
);
