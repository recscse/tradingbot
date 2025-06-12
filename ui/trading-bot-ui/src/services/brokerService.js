import apiClient from "./api";

export const brokerService = {
  // Get all brokers
  async getBrokers() {
    try {
      const response = await apiClient.get("/broker/list");
      return response;
    } catch (error) {
      console.error("Broker service - getBrokers error:", error);
      throw error;
    }
  },

  // Add new broker
  async addBroker(brokerData) {
    try {
      const response = await apiClient.post("/broker/add", brokerData);
      return response;
    } catch (error) {
      console.error("Broker service - addBroker error:", error);
      throw error;
    }
  },

  // Update broker
  async updateBroker(brokerId, brokerData) {
    try {
      const response = await apiClient.put(
        `/api/broker/update/${brokerId}`,
        brokerData
      );
      return response;
    } catch (error) {
      console.error("Broker service - updateBroker error:", error);
      throw error;
    }
  },

  // Delete broker
  async deleteBroker(brokerId) {
    try {
      const response = await apiClient.delete(`/broker/delete/${brokerId}`);
      return response;
    } catch (error) {
      console.error("Broker service - deleteBroker error:", error);
      throw error;
    }
  },

  // Toggle broker status
  async toggleBrokerStatus(brokerId, statusData) {
    try {
      const response = await apiClient.patch(
        `/api/broker/${brokerId}/status`,
        statusData
      );
      return response;
    } catch (error) {
      console.error("Broker service - toggleBrokerStatus error:", error);
      throw error;
    }
  },

  // Test broker connection
  async testBrokerConnection(brokerId) {
    try {
      const response = await apiClient.post(
        `/api/broker/${brokerId}/test-connection`
      );
      return response;
    } catch (error) {
      console.error("Broker service - testBrokerConnection error:", error);
      throw error;
    }
  },
};
