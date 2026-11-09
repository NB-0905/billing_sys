USE restaurant;

-- Run once on the previous version of the project.
-- These changes preserve existing bill and order records.
ALTER TABLE bills
    MODIFY bill_id INT NOT NULL AUTO_INCREMENT;

ALTER TABLE order_details
    ADD COLUMN item_name VARCHAR(50) NULL AFTER item_id;

-- Existing rows receive the item's current menu name during migration.
UPDATE order_details AS od
JOIN menu AS m ON od.item_id = m.item_id
SET od.item_name = m.item_name
WHERE od.item_name IS NULL;

ALTER TABLE order_details
    MODIFY item_name VARCHAR(50) NOT NULL;
