CREATE OR REPLACE FUNCTION get_random_float(seed INT, step INT) 
RETURNS FLOAT AS $$
DECLARE
    hash_hex TEXT;
    hash_int BIGINT;
BEGIN
    hash_hex := md5(seed::TEXT || '-' || step::TEXT);
    hash_int := ('x' || substr(hash_hex, 1, 8))::bit(32)::bigint;
    RETURN hash_int::FLOAT / 4294967295.0;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_random_normal(seed INT, step INT)
RETURNS FLOAT AS $$
DECLARE
    u1 FLOAT; u2 FLOAT;
BEGIN
    u1 := get_random_float(seed, step);
    u2 := get_random_float(seed, step + 1000);
    RETURN SQRT(-2.0 * LN(u1 + 1e-9)) * COS(2.0 * 3.14159 * u2);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pick_from_array(seed INT, step INT, arr TEXT[])
RETURNS TEXT AS $$
DECLARE
    idx INT;
    len INT;
    r FLOAT;
BEGIN
    len := array_length(arr, 1);
    r := get_random_float(seed, step);
    idx := FLOOR(r * len) + 1;
    RETURN arr[idx];
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generate_fake_people(
    input_seed INT, 
    batch_size INT, 
    input_locale TEXT, 
    page_offset INT
)
RETURNS TABLE (
    user_num INT,
    id UUID,
    full_name TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    height_cm INT,
    weight_kg INT,
    eye_color TEXT,
    lat FLOAT,
    lon FLOAT
) AS $$
DECLARE
    i INT;
    row_seed INT;
    
    arr_fnames TEXT[]; arr_lnames TEXT[]; arr_cities TEXT[]; arr_streets TEXT[];
    cnt_fnames INT; cnt_lnames INT; cnt_cities INT; cnt_streets INT;
    
    arr_domains TEXT[] := ARRAY['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'live.com', 'icloud.com'];
    arr_eyes TEXT[] := ARRAY['Blue', 'Brown', 'Green', 'Hazel', 'Grey'];
    arr_titles TEXT[];
    
    r1 FLOAT; r2 FLOAT; r3 FLOAT; r4 FLOAT; r5 FLOAT; r6 FLOAT; r_var FLOAT;
    r_phone FLOAT; r_email_num FLOAT;
    
    sel_fname TEXT; sel_mname TEXT; sel_lname TEXT; sel_city TEXT; sel_street TEXT;
    sel_title TEXT; sel_domain TEXT;
    
BEGIN
    SELECT ARRAY(SELECT name FROM first_names WHERE locale = input_locale) INTO arr_fnames;
    cnt_fnames := array_length(arr_fnames, 1);
    
    SELECT ARRAY(SELECT name FROM last_names WHERE locale = input_locale) INTO arr_lnames;
    cnt_lnames := array_length(arr_lnames, 1);
    
    SELECT ARRAY(SELECT name FROM cities WHERE locale = input_locale) INTO arr_cities;
    cnt_cities := array_length(arr_cities, 1);
    
    SELECT ARRAY(SELECT name FROM streets WHERE locale = input_locale) INTO arr_streets;
    cnt_streets := array_length(arr_streets, 1);

    IF input_locale = 'de_DE' THEN
        arr_titles := ARRAY['Herr', 'Frau', 'Dr.', 'Prof.'];
    ELSIF input_locale = 'fr_FR' THEN
        arr_titles := ARRAY['M.', 'Mme', 'Dr'];
    ELSE
        arr_titles := ARRAY['Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.'];
    END IF;

    FOR i IN 1..batch_size LOOP
        row_seed := input_seed + page_offset + i;
        
        r1 := get_random_float(row_seed, 1);
        r2 := get_random_float(row_seed, 2);
        r3 := get_random_float(row_seed, 3);
        r4 := get_random_float(row_seed, 4);
        
        sel_fname := arr_fnames[FLOOR(r1 * cnt_fnames) + 1];
        sel_lname := arr_lnames[FLOOR(r2 * cnt_lnames) + 1];
        sel_city := arr_cities[FLOOR(r3 * cnt_cities) + 1];
        sel_street := arr_streets[FLOOR(r4 * cnt_streets) + 1];
        
        r_var := get_random_float(row_seed, 100);
        
        IF r_var < 0.2 THEN
            sel_title := pick_from_array(row_seed, 101, arr_titles);
            full_name := sel_title || ' ' || sel_fname || ' ' || sel_lname;
        ELSIF r_var > 0.8 THEN
            sel_mname := arr_fnames[FLOOR(get_random_float(row_seed, 102) * cnt_fnames) + 1];
            full_name := sel_fname || ' ' || sel_mname || ' ' || sel_lname;
        ELSE
            full_name := sel_fname || ' ' || sel_lname;
        END IF;

        r_var := get_random_float(row_seed, 200);
        IF input_locale = 'de_DE' THEN
             address := sel_street || ' ' || FLOOR(r_var * 200 + 1)::TEXT || ', ' || sel_city;
        ELSIF input_locale = 'fr_FR' THEN
             address := FLOOR(r_var * 99 + 1)::TEXT || ' rue ' || sel_street || ', ' || sel_city;
        ELSE
             address := FLOOR(r_var * 999 + 1)::TEXT || ' ' || sel_street || ', ' || sel_city;
        END IF;

        eye_color := pick_from_array(row_seed, 300, arr_eyes);

        -- EMAIL LOGIC (UPDATED)
        sel_domain := pick_from_array(row_seed, 400, arr_domains);
        r_email_num := get_random_float(row_seed, 405); 
        r_var := get_random_float(row_seed, 406);

        -- Choose base format
        IF r_var < 0.25 THEN
             email := lower(sel_fname) || '.' || lower(sel_lname);
        ELSIF r_var < 0.50 THEN
             email := lower(sel_fname) || '_' || lower(sel_lname);
        ELSIF r_var < 0.75 THEN
             email := lower(sel_lname) || '.' || lower(sel_fname);
        ELSE
             email := lower(substring(sel_fname, 1, 1)) || '.' || lower(sel_lname);
        END IF;
        
        -- 30% Chance to add a number (70% Chance NO NUMBER)
        IF get_random_float(row_seed, 407) < 0.3 THEN
            email := email || FLOOR(r_email_num * 99 + 1)::TEXT;
        END IF;

        email := email || '@' || sel_domain;
        -- END EMAIL LOGIC

        height_cm := 175 + (get_random_normal(row_seed, 7) * 10)::INT;
        weight_kg := 80 + (get_random_normal(row_seed, 8) * 15)::INT;
        
        r_phone := get_random_float(row_seed, 500);
        IF input_locale = 'de_DE' THEN
            phone := '+49-1' || FLOOR(r_phone * 9 + 5)::TEXT || '-' || FLOOR(get_random_float(row_seed, 501) * 8999999 + 1000000)::TEXT;
        ELSIF input_locale = 'fr_FR' THEN
            phone := '+33-' || FLOOR(r_phone * 2 + 6)::TEXT || '-' || FLOOR(get_random_float(row_seed, 501) * 89 + 10)::TEXT || '-' || FLOOR(get_random_float(row_seed, 502) * 89 + 10)::TEXT || '-' || FLOOR(get_random_float(row_seed, 503) * 89 + 10)::TEXT;
        ELSE
            phone := '+1-' || FLOOR(r_phone * 800 + 100)::TEXT || '-' || FLOOR(get_random_float(row_seed, 501) * 899 + 100)::TEXT || '-' || FLOOR(get_random_float(row_seed, 502) * 8999 + 1000)::TEXT;
        END IF;

        r5 := get_random_float(row_seed, 5);
        r6 := get_random_float(row_seed, 6);
        lat := (ACOS(2 * r5 - 1) * 180 / 3.14159265) - 90;
        lon := r6 * 360 - 180;
        
        user_num := i + page_offset;
        id := gen_random_uuid();
        
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
