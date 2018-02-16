import numpy as np
import scr.StatisticalClasses as Stat
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
from scr import FigureSupport as Fig


class Strategy:
    def __init__(self, name, cost_obs, effect_obs):
        """
        :param name: name of the strategy
        :param cost_obs: list or numpy.array of cost observations
        :param effect_obs: list or numpy.array of effect observations
        """
        self.name = name
        if type(cost_obs) == list:
            self.costObs = np.array(cost_obs)
        else:
            self.costObs = cost_obs
        if type(effect_obs) == list:
            self.effectObs = np.array(effect_obs)
        else:
            self.effectObs = effect_obs
        self.aveCost = np.average(self.costObs)
        self.aveEffect = np.average(self.effectObs)
        self.ifDominated = False


class CEA:
    """ class for doing cost-effectiveness analysis """

    def __init__(self, strategies, if_paired):
        """
        :param strategies: the list of strategies (assumes that the first strategy represents the "base" strategy)
        :param if_paired: indicate whether the strategies are paired
        """
        self._n = len(strategies)               # number of strategies
        self._strategies = strategies           # list of strategies
        self._strategiesOnFrontier = []         # list of strategies on the frontier
        self._strategiesNotOnFrontier = []      # list of strategies not on the frontier

        # now shift all strategies such as the base strategy (first in the list) lies on the origine
        # all the following data analysis are based on the shifted data
        shifted_strategies = []
        # if observations are paired across strategies
        if if_paired:
            for i in range(self._n):
                shifted_strategy = Strategy(strategies[i].name,
                                            strategies[i].costObs-strategies[0].costObs,
                                            strategies[i].effectObs-strategies[0].effectObs)
                shifted_strategies.append(shifted_strategy)

        else:  # if not paired
            e_cost = strategies[0].aveCost
            e_effect = strategies[0].aveEffect
            for i in range(self._n):
                shifted_strategy = Strategy(strategies[i].name,
                                            strategies[i].costObs - e_cost,
                                            strategies[i].effectObs - e_effect)
                shifted_strategies.append(shifted_strategy)
        self._shifted_strategies = shifted_strategies       # list of shifted strategies

        # create a data frame for all strategies' expected outcomes
        self._dfStrategies = pd.DataFrame(
            index=range(self._n),
            columns=['Name', 'E[Cost]', 'E[Effect]', 'Dominated', 'Color'])

        # populate the data frame
        for j in range(self._n):
            self._dfStrategies.loc[j, 'Name'] = shifted_strategies[j].name
            self._dfStrategies.loc[j, 'E[Cost]'] = shifted_strategies[j].aveCost
            self._dfStrategies.loc[j, 'E[Effect]'] = shifted_strategies[j].aveEffect
            self._dfStrategies.loc[j, 'Dominated'] = shifted_strategies[j].ifDominated
            self._dfStrategies.loc[j, 'Color'] = "k"  # not Dominated black, Dominated blue

        # find the CE frontier
        self.__find_frontier()

    def get_frontier(self):
        """ :return list of strategies on the frontier"""
        return self._strategiesOnFrontier

    def get_none_frontier(self):
        """ :return list of strategies that are not on the frontier """
        return self._strategiesNotOnFrontier

    def __find_frontier(self):
        """ find the cost-effectiveness frontier """

        # sort strategies by cost, ascending
        # operate on local variable data rather than self attribute
        df1 = self._dfStrategies.sort_values('E[Cost]')

        # apply criteria 1
        for i in range(self._n):
            # strategies with higher cost and lower Effect are dominated
            df1.loc[
                (df1['E[Cost]'] > df1['E[Cost]'][i]) &
                (df1['E[Effect]'] <= df1['E[Effect]'][i]),
                'Dominated'] = True
        # change the color of dominated strategies to blue
        df1.loc[df1['Dominated'] == True, 'Color'] = 'blue'

        # apply criteria 2
        # select all non-dominated strategies
        df2 = df1.loc[df1['Dominated']==False]
        n2 = len(df2['E[Cost]'])

        for i in range(0, n2): # can't decide for first and last point
            for j in range(i+1, n2):
                # cost and effect of strategy i
                effect_i = df2['E[Effect]'].iloc[i]
                cost_i = df2['E[Cost]'].iloc[i]
                # cost and effect of strategy j
                effect_j = df2['E[Effect]'].iloc[j]
                cost_j = df2['E[Cost]'].iloc[j]
                # vector connecting strategy i to j
                v_i_to_j = np.array([effect_j-effect_i, cost_j-cost_i])

                # if the effect of no strategy is between the effects of strategies i and j
                if not ((df2['E[Effect]'] > effect_i) & (df2['E[Effect]'] < effect_j)).any():
                    continue    # to the next j
                else:
                    # get all the strategies with effect between strategies i and j
                    inner_points = df2.loc[(df2['E[Effect]'] > effect_i) & (df2['E[Effect]'] < effect_j)]
                    # difference in effect of inner points and strategy i
                    v2_x = inner_points['E[Effect]'] - effect_i
                    # difference in cost of inner points and strategy i
                    v2_y = inner_points['E[Cost]']-cost_i

                    # cross products of vector i to j and the vectors i to all inner points
                    cross_product = v_i_to_j[0] * np.array(v2_y) - v_i_to_j[1] * np.array(v2_x)

                    # if cross_product > 0 the point is above the line
                    # (because the point are sorted vertically)
                    # ref: How to tell whether a point is to the right or left side of a line
                    # https://stackoverflow.com/questions/1560492
                    dominated_index = inner_points[cross_product > 0].index
                    df1.loc[list(dominated_index), 'Dominated'] = True
                    df1.loc[list(dominated_index), 'Color'] = 'blue'

        # update strategies
        self._dfStrategies = df1

        # create list of strategies on frontier
        on_frontier_index = df1[df1['Dominated'] == False].index
        for i in on_frontier_index:
            self._strategiesOnFrontier.append(self._strategies[i])

        # create list of strategies not on frontier
        not_on_frontier_index = df1[df1['Dominated'] == True].index
        for j in not_on_frontier_index:
            self._strategiesNotOnFrontier.append(self._strategies[j])

    def show_CE_plane(self, title, x_label, y_label, show_names=False, show_clouds=False,
                      show_legend=False, figure_size=6):
        """
        :param title: title of the figure
        :param x_label: (string) x-axis label
        :param y_label: (string) y-axis label
        :param show_names: logical, show strategy names
        :param show_clouds: logical, show true sample observation of strategies
        :param show_legend: shows the legend of strategies, would only be used when show_clouds is true
        :param figure_size: int, specify the figure size
        """
        # plots
        # operate on local variable data rather than self attribute
        data = self._dfStrategies

        # re-sorted according to Effect to draw line
        line_plot = data.loc[data["Dominated"] == False].sort_values('E[Effect]')

        # show observation clouds for strategies
        if show_clouds:
            plt.figure(figsize=(figure_size, figure_size))
            for strategy_i, color in zip(self._shifted_strategies, cm.rainbow(np.linspace(0, 1, self._n))):
                x_values = strategy_i.effectObs
                y_values = strategy_i.costObs
                # plot clouds
                plt.scatter(x_values, y_values, c=color, alpha=0.5, s=25, label=strategy_i.name)
            if show_legend:
                plt.legend() # to customize legend: loc='lower right', numpoints=1, ncol=3, fontsize=8)
            plt.scatter(data['E[Effect]'], data['E[Cost]'], marker='x', c='k', s=50, linewidths=2)

        else:
            plt.figure(figsize=(figure_size, figure_size))
            plt.scatter(data['E[Effect]'], data['E[Cost]'], c=list(data['Color']), s=50)

        plt.plot(line_plot['E[Effect]'], line_plot['E[Cost]'], c='k')
        plt.axhline(y=0, c='k',linewidth=0.5)
        plt.axvline(x=0, c='k',linewidth=0.5)
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)

        # show names of strategies
        if show_names:
            if not show_clouds:
                for label, x, y in zip(data['Name'], data['E[Effect]'], data['E[Cost]']):
                    plt.annotate(
                        label, xy=(x, y), xycoords='data', xytext=(x - 0.6, y + 0.3),
                        textcoords='data',weight='bold')

            elif show_clouds:
                for label, x, y in zip(data['Name'], data['E[Effect]'], data['E[Cost]']):
                    plt.annotate(
                        label,
                        xy=(x, y), xycoords='data', xytext=(x-0.8, y+0.8), textcoords='data',
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3', shrinkA=0, shrinkB=2),
                        weight='bold', bbox=dict(pad=0, facecolor="none", edgecolor="none"))

        # show the figure
        Fig.output_figure(plt, Fig.OutType.SHOW, title)

    def build_CE_table(self, cost_digits=0, effect_digits=2, icer_digits=1):
        """
        :param cost_digits: digits to round cost estimates to
        :param effect_digits: digits to round effect estimate to
        :param icer_digits: digits to round ICER estimates to
        :return: output csv file called "CETable.csv" in local environment
        """

        # initialize the table
        table = self._dfStrategies
        table['E[dCost]'] = "-"
        table['E[dEffect]'] = "-"
        table['ICER'] = "Dominated"

        # get strategies on the frontier
        frontier_strategies = table.loc[table["Dominated"] == False].sort_values('E[Cost]')
        # number of strategies on the frontier
        n_frontier_strategies = frontier_strategies.shape[0]

        incr_cost = []      # list of incremental costs
        incr_effect = []    # list of incremental effects
        ICER = []           # list of ICER estimates

        # calculate incremental costs, incremental effects and ICER
        for i in range(1, n_frontier_strategies):
            # incremental cost
            d_cost = frontier_strategies["E[Cost]"].iloc[i]-frontier_strategies["E[Cost]"].iloc[i-1]
            incr_cost = np.append(incr_cost, d_cost)
            # incremental effect
            d_effect = frontier_strategies["E[Effect]"].iloc[i]-frontier_strategies["E[Effect]"].iloc[i-1]
            if d_effect == 0:
                raise ValueError('invalid value of E[dEffect], the ratio is not computable')
            incr_effect = np.append(incr_effect, d_effect)
            # ICER
            ICER = np.append(ICER, d_cost/d_effect)

        # format the numbers
        ind_change = frontier_strategies.index[1:]
        table.loc[ind_change, 'E[dCost]'] = incr_cost.astype(float).round(cost_digits)
        table.loc[ind_change, 'E[dEffect]'] = incr_effect.astype(float).round(effect_digits)
        table.loc[ind_change, 'ICER'] = ICER.astype(float).round(icer_digits)
        table.loc[frontier_strategies.index[0], 'ICER'] = '-'

        # create output dataframe
        # python round will leave trailing 0 for 0 decimal
        if cost_digits == 0:
            output_cost = table['E[Cost]'].astype(int)
        else:
            output_cost = table['E[Cost]'].astype(float).round(cost_digits)

        if effect_digits == 0:
            output_effect = table['E[Effect]'].astype(int)
        else:
            output_effect = table['E[Effect]'].astype(float).round(effect_digits)

        # output table
        output = pd.DataFrame(
            {'Name': table['Name'],
             'E[Cost]': output_cost,
             'E[Effect]': output_effect,
             'E[dCost]': table['E[dCost]'],
             'E[dEffect]': table['E[dEffect]'],
             'ICER': table['ICER']
             })

        output = output[['Name', 'E[Cost]', 'E[Effect]', 'E[dCost]', 'E[dEffect]', 'ICER']]

        # write csv
        output.to_csv("CETable.csv", encoding='utf-8', index=False)

        return output


class ComparativeEconMeasure():
    def __init__(self, name, cost_new, health_new, cost_base, health_base):
        """
        :param name: descrition
        :param cost_new: (list or numpy.array) cost data for the new strategy
        :param health_new: (list or numpy.array) health data for the new strategy
        :param cost_base: (list or numpy.array) cost data for teh base line
        :param health_base: (list or numpy.array) health data for the base line
        """

        self._name = name
        self._costNew = None        # cost data for the new strategy
        self._healthNew = None      # health data for the new strategy
        self._costBase = None      # cost data for teh base line
        self._healthBase = None    # health data for the base line

        # convert input data to numpy.array if needed
        if type(cost_new) == list:
            self._costNew = np.array(cost_new)
        if type(health_new) == list:
            self._healthNew = np.array(health_new)
        if type(cost_base) == list:
            self._costBase = np.array(cost_base)
        if type(health_base) == list:
            self._healthBase = np.array(health_base)

        # calculate the difference in average cost and health
        self._delta_ave_cost = np.average(self._costNew) - np.average(self._costBase)
        self._delta_ave_health = np.average(self._healthNew) - np.average(self._healthBase)


class ICER(ComparativeEconMeasure):
    def __init__(self, name, cost_new, health_new, cost_base, health_base):
        # initialize the base class
        ComparativeEconMeasure.__init__(self, name, cost_new, health_new, cost_base, health_base)
        # calcualte ICER
        self._ICER = self._delta_ave_cost/self._delta_ave_health

    def get_ICER(self):
        """ return ICER """
        return self._ICER

    def get_CI(self, alpha, num_bootstrap_samples):
        """
        :param alpha: significance level, a value from [0, 1]
        :param num_bootstrap_samples: number of bootstrap samples
        :return: confidence interval in the format of list [l, u]
        """
        # abstract method to be overridden in derived classes to process an event
        raise NotImplementedError("This is an abstract method and needs to be implemented in derived classes.")

    def get_PI(self, alpha):
        """
        :param alpha: significance level, a value from [0, 1]
        :return: percentile interval in the format of list [l, u]
        """
        # abstract method to be overridden in derived classes to process an event
        raise NotImplementedError("This is an abstract method and needs to be implemented in derived classes.")


class ICER_paired(ICER):

    def __init__(self, name, cost_new, health_new, cost_base, health_base):
        # initialize the base class
        ICER.__init__(name, cost_new, health_new, cost_base, health_base)

        # incremental observations
        self._deltaCost = self._costNew - self._costBase
        self._deltaHealth = self._healthNew - self._healthBase

        # create a ratio stat
        self._ratio_stat = Stat.RatioStatPaired(name, self._deltaCost, self._deltaHealth)

    def get_CI(self, alpha, num_bootstrap_samples):

        # bootstrap algorithm
        ICERs = np.zeros(num_bootstrap_samples)
        for i in range(num_bootstrap_samples):
            d_cost = np.random.choice(self._deltaCost, size=len(self._deltaCost), replace=True)
            d_health = np.random.choice(self._deltaHealth, size=len(self._deltaHealth), replace=True)

            ave_d_cost = np.average(d_cost)
            ave_d_health = np.average(d_health)

            # assert all the means should not be 0
            if np.average(ave_d_health) == 0:
                raise ValueError('invalid value of mean of y, the ratio is not computable')

            ICERs[i] = ave_d_cost/ave_d_health - self._ICER

        return self._ICER - np.percentile(ICERs, [100 * (1 - alpha / 2.0), 100 * alpha / 2.0])

    def get_PI(self, alpha):
        return self._ratio_stat.get_PI(alpha)


class ICER_indp(ICER):

    def __init__(self, name, cost_new, health_new, cost_base, health_base):
        # initialize the base class
        ICER.__init__(name, cost_new, health_new, cost_base, health_base)

    def get_CI(self, alpha, num_bootstrap_samples):
        pass

    def get_PI(self, alpha):
        pass


class NMB(ComparativeEconMeasure):
    def __init__(self, name, cost_new, health_new, cost_base, health_base):
        # initialize the base class
        ComparativeEconMeasure.__init__(self, name, cost_new, health_new, cost_base, health_base)

    def get_NMB(self, wtp):
        """
        :param wtp: willingness-to-pay
        :returns: the net monetary benefit at the provided willingness-to-pay value
        """
        return wtp * self._delta_ave_health - self._delta_ave_cost

    def get_CI(self, wtp, alpha):
        """
        :param wtp: willingness-to-pay value
        :param alpha: significance level, a value from [0, 1]
        :return: confidence interval in the format of list [l, u]
        """
        # abstract method to be overridden in derived classes to process an event
        raise NotImplementedError("This is an abstract method and needs to be implemented in derived classes.")

    def get_PI(self, wtp, alpha):
        """
        :param wtp: willingness-to-pay value
        :param alpha: significance level, a value from [0, 1]
        :return: percentile interval in the format of list [l, u]
        """
        # abstract method to be overridden in derived classes to process an event
        raise NotImplementedError("This is an abstract method and needs to be implemented in derived classes.")


class NMB_paired(NMB):

    def __init__(self, name, cost_new, health_new, cost_base, health_base):
        NMB.__init__(name, cost_new, health_new, cost_base, health_base)

        # incremental observations
        self._deltaCost = self._costNew - self._costBase
        self._deltaHealth = self._healthNew - self._healthBase

    def get_CI(self, wtp, alpha):

        # create a sumary statistics
        stat = Stat.SummaryStat(self._name, wtp * self._deltaHealth - self._deltaCost)
        return stat.get_t_CI(alpha)

    def get_PI(self, wtp, alpha):

        # create a summary statistics
        stat = Stat.SummaryStat(self._name, wtp * self._deltaHealth - self._deltaCost)
        return stat.get_PI(alpha)


class NMB_indp(NMB):

    def __init__(self, name, cost_new, health_new, cost_base, health_base):
        NMB.__init__(name, cost_new, health_new, cost_base, health_base)

    def get_CI(self, wtp, alpha):
        pass

    def get_PI(self, wtp, alpha):
        pass