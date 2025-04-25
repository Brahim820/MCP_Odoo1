SERVEUR ODOO MCP - GUIDE D'INSTALLATION
Préparation

    Installer Claude Desktop :
        Téléchargez Claude Desktop depuis https://claude.ai/download
        Suivez les instructions d'installation pour finaliser le processus
        Assurez-vous que Claude Desktop a été exécuté au moins une fois pour créer le dossier de configuration

    Installer Python 3.13 ou une version supérieure :
        Si Python n'est pas installé, téléchargez-le depuis https://www.python.org/downloads/
        Assurez-vous de cocher l'option "Add Python to PATH" pendant l'installation
        Si vous avez déjà Python installé, vous pouvez utiliser cette commande pour le mettre à jour : winget install Python.Python.3.13

Étapes d'installation

    Exécuter l'installateur :
        Extrayez tous les fichiers ZIP dans un nouveau dossier
        Double-cliquez sur le fichier install_mcp_odoo_simple.bat
        Attendez que le processus d'installation soit terminé
        Ne fermez pas la fenêtre de l'installateur avant l'apparition du message "INSTALLATION TERMINÉE"

    Configurer les identifiants Odoo :
        Après l'installation, vous devrez modifier les identifiants Odoo si nécessaire
        Vous pouvez trouver le chemin du fichier claude_desktop_config.json en cliquant sur le menu "File -> Settings" dans Claude Desktop
        Sélectionnez l'onglet Developer et cliquez sur "Edit Config"
        Modifiez les sections suivantes en fonction de vos identifiants Odoo :
        JSON

        "env": {
          "PYTHONPATH": "...",
          "ODOO_URL": "https://api-odoo.visiniaga.com",
          "ODOO_DB": "OdooDev",
          "ODOO_USER": "od@visiniaga.com",
          "ODOO_PASSWORD": "Passwoord"
        }

    Redémarrer Claude Desktop :
        Fermez Claude Desktop s'il est en cours d'exécution
        Rouvrez Claude Desktop pour charger la nouvelle configuration

    Configurer l'agent AI :
        Créez un nouveau projet
        Remplissez le prompt à partir du fichier system prompt baru.txt dans la section Knowledge Base

Utilisation

Une fois l'installation terminée, vous pouvez utiliser Claude pour :

    Explorer les modèles Odoo :
        Demandez à Claude : "Affichez la liste des modèles Odoo disponibles"
        Ou : "Montrez le schéma du modèle res.partner"

    Rechercher des données :
        Demandez à Claude : "Recherchez les 10 principaux clients dans Odoo"
        Ou : "Affichez la liste des commandes de vente de ce mois-ci"

    Créer des rapports :
        Demandez à Claude : "Créez un rapport de ventes par produit"
        Ou : "Analysez les stocks par emplacement"

Désinstallation du programme

Si vous souhaitez supprimer le serveur MCP Odoo :

    Exécutez uninstall_mcp_odoo_simple.bat
    Suivez les instructions affichées
    Redémarrez Claude Desktop après la désinstallation

Résolution des problèmes

En cas de problème :

    Claude n'affiche pas l'icône MCP (icône de marteau en bas à droite) :
        Vérifiez que le fichier de configuration est correct
        Redémarrez Claude Desktop

    Erreur de connexion Odoo :
        Vérifiez les identifiants Odoo dans le fichier de configuration
        Assurez-vous que l'URL Odoo est accessible depuis votre ordinateur

    Erreur Python :
        Assurez-vous que Python est correctement installé
        Essayez de réinstaller en relançant l'installateur
