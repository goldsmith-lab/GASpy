from gaspy.tasks import schedule_tasks
from gaspy.gasdb import get_catalog_docs
from gaspy.tasks.metadata_calculators import CalculateAdsorptionEnergy


# Get all of the sites that we have enumerated
all_site_documents = get_catalog_docs()

# Pick the sites that we want to run. In this case, it'll be sites on
# palladium (as per Materials Project ID 2, mp-2) on (111) facets.
site_documents_to_calc = [doc for doc in all_site_documents
                          if (doc['mpid'] == 'mp-33' and
                              doc['miller'] == [1, 1, 1])]

# Turn the sites into GASpy/Luigi tasks
tasks = [CalculateAdsorptionEnergy(adsorbate_name='H',
                                   adsorption_site=doc['adsorption_site'],
                                   mpid=doc['mpid'],
                                   miller_indices=doc['miller'],
                                   shift=doc['shift'],
                                   top=doc['top'])
         for doc in site_documents_to_calc]

# Schedule/run all of the tasks
schedule_tasks(tasks)
