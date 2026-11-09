USE restaurant;

-- Run once on an existing database. This preserves existing bills.
ALTER TABLE bills
    MODIFY bill_id INT NOT NULL AUTO_INCREMENT;
