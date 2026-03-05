-- ============================================================
-- Jeu de données de test — 40 bouteilles variées
-- À exécuter dans le SQL Editor de Supabase
-- ============================================================

INSERT INTO bottles (name, color, region, appellation, producer, vintage, grape_varieties, purchase_price, quantity, storage_location, drink_from, drink_until, notes)
VALUES

-- BORDEAUX ROUGES
('Château Margaux',          'rouge', 'Bordeaux',   'Margaux',             'Château Margaux',          2016, ARRAY['Cabernet Sauvignon','Merlot'],  320.00,  2, 'Cave principale',  2024, 2045, 'Grand cru classé, tannins soyeux'),
('Château Pichon Baron',     'rouge', 'Bordeaux',   'Pauillac',            'Pichon Baron',             2018, ARRAY['Cabernet Sauvignon','Merlot'],  110.00,  3, 'Cave principale',  2025, 2040, NULL),
('Château Lynch-Bages',      'rouge', 'Bordeaux',   'Pauillac',            'Château Lynch-Bages',      2015, ARRAY['Cabernet Sauvignon','Merlot'],   95.00,  2, 'Cave principale',  2022, 2038, 'Très classique, cassis et cèdre'),
('Château Léoville Barton',  'rouge', 'Bordeaux',   'Saint-Julien',        'Léoville Barton',          2017, ARRAY['Cabernet Sauvignon','Merlot'],   75.00,  4, 'Cave secondaire',  2024, 2040, NULL),
('Château La Conseillante',  'rouge', 'Bordeaux',   'Pomerol',             'Château La Conseillante',  2019, ARRAY['Merlot','Cabernet Franc'],       150.00,  1, 'Cave principale',  2026, 2042, 'Velours et fruits rouges'),
('Château Figeac',           'rouge', 'Bordeaux',   'Saint-Émilion',       'Château Figeac',           2014, ARRAY['Cabernet Franc','Merlot'],       120.00,  3, 'Cave principale',  2022, 2038, NULL),
('Château Rauzan-Ségla',     'rouge', 'Bordeaux',   'Margaux',             'Rauzan-Ségla',             2016, ARRAY['Cabernet Sauvignon','Merlot'],   65.00,  2, 'Cave secondaire',  2023, 2036, NULL),

-- BOURGOGNE ROUGES
('Gevrey-Chambertin 1er Cru','rouge', 'Bourgogne',  'Gevrey-Chambertin',   'Rossignol-Trapet',         2020, ARRAY['Pinot Noir'],                    85.00,  3, 'Cave principale',  2025, 2038, 'Fruité, épicé, belle longueur'),
('Chambolle-Musigny',        'rouge', 'Bourgogne',  'Chambolle-Musigny',   'Domaine Mugnier',          2018, ARRAY['Pinot Noir'],                   180.00,  1, 'Cave principale',  2024, 2035, 'Floral et délicat'),
('Volnay Caillerets',        'rouge', 'Bourgogne',  'Volnay',              'Domaine de la Pousse d''Or',2019, ARRAY['Pinot Noir'],                   95.00,  2, 'Cave principale',  2025, 2037, NULL),
('Pommard Les Rugiens',      'rouge', 'Bourgogne',  'Pommard',             'Domaine Lejeune',          2017, ARRAY['Pinot Noir'],                    70.00,  2, 'Cave secondaire',  2023, 2034, 'Structure tannique ferme'),
('Nuits-Saint-Georges',      'rouge', 'Bourgogne',  'Nuits-Saint-Georges', 'Henri Gouges',             2021, ARRAY['Pinot Noir'],                    55.00,  4, 'Cave secondaire',  2025, 2033, NULL),

-- CÔTE DU RHÔNE ROUGES
('Châteauneuf-du-Pape',      'rouge', 'Rhône',      'Châteauneuf-du-Pape', 'Château Rayas',            2017, ARRAY['Grenache'],                     220.00,  1, 'Cave principale',  2024, 2040, 'Légendaire, complexe et profond'),
('Hermitage',                'rouge', 'Rhône',      'Hermitage',           'Jean-Louis Chave',         2015, ARRAY['Syrah'],                        280.00,  1, 'Cave principale',  2025, 2045, 'Monument du Rhône'),
('Crozes-Hermitage',         'rouge', 'Rhône',      'Crozes-Hermitage',    'Domaine Combier',          2022, ARRAY['Syrah'],                         28.00,  5, 'Frigo à vin',      2023, 2030, 'Rapport qualité/prix excellent'),
('Gigondas',                 'rouge', 'Rhône',      'Gigondas',            'Domaine Saint-Damien',     2020, ARRAY['Grenache','Syrah','Mourvèdre'],   32.00,  4, 'Cave secondaire',  2023, 2032, NULL),
('Cairanne',                 'rouge', 'Rhône',      'Cairanne',            'Domaine Richaud',          2021, ARRAY['Grenache','Mourvèdre'],           22.00,  6, 'Frigo à vin',      2023, 2030, NULL),

-- LANGUEDOC / SUD ROUGES
('Mas de Daumas Gassac',     'rouge', 'Languedoc',  'Hérault IGP',         'Mas de Daumas Gassac',     2018, ARRAY['Cabernet Sauvignon'],             45.00,  3, 'Cave secondaire',  2023, 2035, 'Le Latour du Languedoc'),
('La Grange des Pères',      'rouge', 'Languedoc',  'Hérault IGP',         'La Grange des Pères',      2017, ARRAY['Syrah','Mourvèdre'],             120.00,  2, 'Cave principale',  2025, 2040, 'Culte et rare'),

-- LOIRE ROUGES
('Bourgueil Vieilles Vignes', 'rouge','Loire',      'Bourgueil',           'Domaine de la Butte',      2020, ARRAY['Cabernet Franc'],                 18.00,  6, 'Frigo à vin',      2022, 2030, 'Frais, fruité, facile'),
('Saumur-Champigny',         'rouge', 'Loire',      'Saumur-Champigny',    'Domaine Filliatreau',      2021, ARRAY['Cabernet Franc'],                 15.00,  5, 'Frigo à vin',      2022, 2028, NULL),

-- BOURGOGNE BLANCS
('Meursault Les Charmes',    'blanc', 'Bourgogne',  'Meursault',           'Domaine Lafon',            2019, ARRAY['Chardonnay'],                   145.00,  2, 'Cave principale',  2023, 2032, 'Beurré, noisette, minéral'),
('Puligny-Montrachet',       'blanc', 'Bourgogne',  'Puligny-Montrachet',  'Domaine Leflaive',         2020, ARRAY['Chardonnay'],                   180.00,  1, 'Cave principale',  2024, 2033, NULL),
('Chablis Premier Cru',      'blanc', 'Bourgogne',  'Chablis',             'William Fèvre',            2021, ARRAY['Chardonnay'],                    38.00,  4, 'Frigo à vin',      2023, 2030, 'Iodé, vif, tranchant'),
('Mâcon-Villages',           'blanc', 'Bourgogne',  'Mâcon',               'Domaine Guffens-Heynen',   2022, ARRAY['Chardonnay'],                    22.00,  5, 'Frigo à vin',      2023, 2027, NULL),

-- ALSACE BLANCS
('Riesling Grand Cru Schlossberg','blanc','Alsace', 'Alsace Grand Cru',    'Domaine Weinbach',         2019, ARRAY['Riesling'],                       55.00,  3, 'Cave principale',  2024, 2040, 'Grande minéralité, agrumes'),
('Gewurztraminer Vendanges Tardives','blanc','Alsace','Alsace',            'Trimbach',                 2018, ARRAY['Gewurztraminer'],                 48.00,  2, 'Cave principale',  2024, 2038, 'Litchi, rose, miel'),

-- LOIRE BLANCS
('Sancerre Blanc',           'blanc', 'Loire',      'Sancerre',            'Henri Bourgeois',          2022, ARRAY['Sauvignon Blanc'],                24.00,  4, 'Frigo à vin',      2023, 2028, 'Sauvignon de référence'),
('Pouilly-Fumé',             'blanc', 'Loire',      'Pouilly-Fumé',        'Didier Dagueneau',         2020, ARRAY['Sauvignon Blanc'],                65.00,  2, 'Cave principale',  2023, 2030, 'Silex, tension, longueur'),
('Muscadet Sèvre et Maine',  'blanc', 'Loire',      'Muscadet',            'Domaine de la Pépière',    2021, ARRAY['Melon de Bourgogne'],              12.00,  6, 'Frigo à vin',      2022, 2026, 'Sur lies, fruits de mer'),

-- RHÔNE BLANCS
('Condrieu',                 'blanc', 'Rhône',      'Condrieu',            'Georges Vernay',           2021, ARRAY['Viognier'],                       65.00,  2, 'Frigo à vin',      2022, 2028, 'Abricot, fleurs blanches, onctueux'),
('Crozes-Hermitage Blanc',   'blanc', 'Rhône',      'Crozes-Hermitage',    'Domaine Combier',          2022, ARRAY['Marsanne','Roussanne'],            26.00,  3, 'Frigo à vin',      2023, 2030, NULL),

-- ROSÉS
('Bandol Rosé',              'rosé',  'Provence',   'Bandol',              'Domaine Tempier',          2022, ARRAY['Mourvèdre','Grenache','Cinsault'],  28.00,  5, 'Frigo à vin',      2023, 2026, 'Le rosé de gastronomie'),
('Palette Rosé',             'rosé',  'Provence',   'Palette',             'Château Simone',           2022, ARRAY['Grenache','Mourvèdre'],             35.00,  3, 'Frigo à vin',      2023, 2027, 'Rare et singulier'),
('Sancerre Rosé',            'rosé',  'Loire',      'Sancerre',            'Henri Bourgeois',          2023, ARRAY['Pinot Noir'],                      22.00,  4, 'Frigo à vin',      2024, 2026, NULL),

-- CHAMPAGNES & MOUSSEUX
('Champagne Blanc de Blancs', 'champagne','Champagne','Champagne',         'Billecart-Salmon',         2015, ARRAY['Chardonnay'],                      95.00,  2, 'Frigo à vin',      2023, 2030, 'Millésimé, crémeux et vif'),
('Champagne Brut NV',        'champagne','Champagne','Champagne',          'Louis Roederer',           NULL, ARRAY['Pinot Noir','Chardonnay','Meunier'], 42.00, 3, 'Frigo à vin',      NULL, NULL,  'Brut de référence, toujours dispo'),

-- LIQUOREUX
('Sauternes',                'liquoreux','Bordeaux', 'Sauternes',          'Château Guiraud',          2016, ARRAY['Sémillon','Sauvignon Blanc'],       45.00,  2, 'Cave principale',  2024, 2045, 'Botrytis magnifique, miel et abricot'),
('Coteaux du Layon',         'liquoreux','Loire',    'Coteaux du Layon',   'Domaine des Baumard',      2018, ARRAY['Chenin Blanc'],                     28.00,  2, 'Cave principale',  2025, 2040, NULL),
('Jurançon Moelleux',        'liquoreux','Sud-Ouest','Jurançon',           'Domaine Cauhapé',          2019, ARRAY['Petit Manseng'],                    22.00,  3, 'Cave principale',  2024, 2038, 'Ananas, mangue, vivacité');
