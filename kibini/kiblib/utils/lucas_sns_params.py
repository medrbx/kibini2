# PARAMETRES POUR LES GRAPHIQUES

from matplotlib import pyplot as plt

params = {'axes.titlesize': 15,
          'axes.titleweight':'bold',
          'axes.grid':'y',
          'axes.labelweight':'bold',
          'legend.shadow':True,
          'figure.subplot.hspace': 0.3,
          'figure.figsize':(15,6),
         }

plt.rcParams.update(params)