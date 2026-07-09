-- ScholarSource v2 RAG domain policy rules.
-- Replaces the hardcoded REJECTED_DOMAINS / PREFERRED_DOMAINS constants so
-- new domains can be added without a deploy. Not an allowlist/blocklist
-- pair: 'preferred' rows are a fast-accept list, and a domain matching no
-- row is still accepted by default checks. 'rejected' is the only hard
-- filter. A 'domain' rule matches the domain and its subdomains; a 'suffix'
-- rule matches any host ending with the pattern (e.g. '.edu').

CREATE TABLE IF NOT EXISTS rag_domain_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern TEXT NOT NULL,
    match_type TEXT NOT NULL CHECK (match_type IN ('domain', 'suffix')),
    policy TEXT NOT NULL CHECK (policy IN ('rejected', 'preferred')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pattern, match_type)
);

CREATE INDEX IF NOT EXISTS idx_rag_domain_policies_policy
    ON rag_domain_policies(policy);

ALTER TABLE rag_domain_policies ENABLE ROW LEVEL SECURITY;

-- Day-one policy. Rejected: paywalled answer mills, scraped-content
-- aggregators, and pages with no extractable study text. Never cite these.
INSERT INTO rag_domain_policies (pattern, match_type, policy, reason) VALUES
    ('chegg.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('coursehero.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('studocu.com', 'domain', 'rejected', 'scraped-content aggregator'),
    ('scribd.com', 'domain', 'rejected', 'paywalled document aggregator'),
    ('numerade.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('bartleby.com', 'domain', 'rejected', 'paywalled answer mill'),
    ('quizlet.com', 'domain', 'rejected', 'no extractable study text'),
    ('slideshare.net', 'domain', 'rejected', 'no extractable study text'),
    ('pinterest.com', 'domain', 'rejected', 'no extractable study text'),
    ('khanacademy.org', 'domain', 'preferred', 'open education source'),
    ('openstax.org', 'domain', 'preferred', 'open textbook publisher'),
    ('libretexts.org', 'domain', 'preferred', 'open textbook publisher'),
    ('ocw.mit.edu', 'domain', 'preferred', 'open courseware'),
    ('wikipedia.org', 'domain', 'preferred', 'open encyclopedia'),
    ('brilliant.org', 'domain', 'preferred', 'interactive courseware'),
    ('.edu', 'suffix', 'preferred', 'accredited US institution'),
    ('.gov', 'suffix', 'preferred', 'government publication'),
    ('.ac.uk', 'suffix', 'preferred', 'accredited UK institution')
ON CONFLICT (pattern, match_type) DO NOTHING;
